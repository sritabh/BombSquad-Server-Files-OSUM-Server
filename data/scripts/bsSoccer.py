import bs
import bsGame
import bsMap
import time
import os
import math
import bsInternal
import bsUtils
import random
import bsVector

def bsGetAPIVersion():
    # see bombsquadgame.com/apichanges
    return 4

def bsGetGames():
    return [FootballGame]

class PuckDeathMessage(object):
    """A puck has died."""
    def __init__(self,puck):
        self.puck = puck

class Puck(bs.Actor):

    def __init__(self,position=(0,1,0)):
        bs.Actor.__init__(self)

        activity = self.getActivity()
        
        # spawn just above the provided point
        self._spawnPos = (position[0],position[1]+1.0,position[2])
        self.lastPlayersToTouch = {}
        self.node = bs.newNode("prop",
                               attrs={'model': activity._puckModel,
                                      'colorTexture': activity._puckTex,
                                      'body':'sphere',
                                      'reflection':'soft',
                                      'reflectionScale':[0.0],
                                      'modelScale':0.3,
                                      'bodyScale':1.0,
                                      'shadowSize': 0.5,
                                      'isAreaOfInterest':True,
                                      'position':self._spawnPos,
                                      'materials': [bs.getSharedObject('objectMaterial'),activity._puckMaterial]
                                      },
                               delegate=self)

    def handleMessage(self,m):
        if isinstance(m,bs.DieMessage):
            self.node.delete()
            activity = self._activity()
            if activity and not m.immediate:
                activity.handleMessage(PuckDeathMessage(self))

        # if we go out of bounds, move back to where we started...
        elif isinstance(m,bs.OutOfBoundsMessage):
            self.node.position = self._spawnPos

        elif isinstance(m,bs.HitMessage):
            self.node.handleMessage("impulse",m.pos[0],m.pos[1],m.pos[2],
                                    m.velocity[0],m.velocity[1],m.velocity[2],
                                    1.0*m.magnitude,1.0*m.velocityMagnitude,m.radius,0,
                                    m.forceDirection[0],m.forceDirection[1],m.forceDirection[2])

            # if this hit came from a player, log them as the last to touch us
            if m.sourcePlayer is not None:
                activity = self._activity()
                if activity:
                    if m.sourcePlayer in activity.players:
                        self.lastPlayersToTouch[m.sourcePlayer.getTeam().getID()] = m.sourcePlayer
        else:
            bs.Actor.handleMessage(self,m)


class FootballGame(bs.TeamGameActivity): 
    tips = ['Do not ask for adminship you will get banned']

     
    @classmethod
    def getName(cls):
        return 'Football' 

    @classmethod
    def getDescription(cls,sessionType):
        return 'Score some goals'

    @classmethod
    def supportsSessionType(cls,sessionType):
        return True if issubclass(sessionType,bs.TeamsSession) else False

    @classmethod
    def getSupportedMaps(cls,sessionType):
        return bs.getMapsSupportingPlayType('teamFlag')

    @classmethod
    def getSettings(cls,sessionType):
        return [("Score to Win",{'minValue':1,'default':10,'increment':1}),
                ("Time Limit",{'choices':[('None',0),('1 Minute',60),
                                          ('2 Minutes',120),('5 Minutes',300),
                                          ('10 Minutes',600),('20 Minutes',1200)],'default':300}),
                                                              ("Night Mode",{'default':False}),
                                          ("Speed",{'default':False}),
                                          ("Epic Mode",{'default':False}),
                ("Respawn Times",{'choices':[('Shorter',0.0),('Short',0.5),('Normal',1.0),('Long',2.0),('Longer',4.0)],'default':0.0})]

    def __init__(self,settings):
        bs.TeamGameActivity.__init__(self,settings)
        self._scoreBoard = bs.ScoreBoard()
        if self.settings['Epic Mode']: self._isSlowMotion = True

        self._cheerSound = bs.getSound("cheer")
        self._chantSound = bs.getSound("")
        self._glSound = bs.getSound("orchestraHitBig2")
        self._swipSound = bs.getSound("")
        self._spwnSound = bs.getSound("orchestraHitBig1")
        self._puckModel = bs.getModel("shield")
        self._puckTex = bs.getTexture("levelIcon")
      #self._puckSound = bs.getSound("block")
        self._rollSound = bs.getSound("bombRoll01")
        self._dinkSounds = (bs.getSound('bombDrop01'),
                           bs.getSound('bombDrop02'))

        self._puckMaterial = bs.Material()
        self._puckMaterial.addActions(
            conditions=('theyHaveMaterial',bs.getSharedObject('footingMaterial')),
            actions=(('impactSound',self._dinkSounds,2,0.8),
                     ('rollSound',self._rollSound,3,6)))
        self._puckMaterial.addActions(actions=( ("modifyPartCollision","friction",500.0)))
        self._puckMaterial.addActions(conditions=("theyHaveMaterial",bs.getSharedObject('pickupMaterial')),
                                      actions=( ("modifyPartCollision","collide",True) ) )
        self._puckMaterial.addActions(conditions=( ("weAreYoungerThan",100),'and',
                                                   ("theyHaveMaterial",bs.getSharedObject('objectMaterial')) ),
                                      actions=( ("modifyNodeCollision","collide",False) ) )
      #  self._puckMaterial.addActions(conditions=("theyHaveMaterial",bs.getSharedObject('footingMaterial')),
      #                                actions=(("impactSound",self._puckSound,0.2,2)))
        # keep track of which player last touched the puck
        self._puckMaterial.addActions(conditions=("theyHaveMaterial",bs.getSharedObject('playerMaterial')),
                                      actions=(("call","atConnect",self._handlePuckPlayerCollide),))
        # we want physical
        self._puckMaterial.addActions(conditions=("theyHaveMaterial",bs.Powerup.getFactory().powerupMaterial),
                                      actions=(("modifyPartCollision","physical",True),
                                               ("message","theirNode","atConnect",bs.DieMessage())))
        self._scoreRegionMaterial = bs.Material()
        self._scoreRegionMaterial.addActions(conditions=("theyHaveMaterial",self._puckMaterial),
                                             actions=(("modifyPartCollision","collide",True),
                                                      ("modifyPartCollision","physical",False),
                                                      ("call","atConnect",self._handleScore)))

    def getInstanceDescription(self):
        return ('Score some goals')

    def getInstanceScoreBoardDescription(self):
     return ('Score ${ARG1} Goals.',self.settings['Score to Win'])
#s = self.settings['Score to Win']
#return 'score '+ str(s)+' goal'+('s' if s > 1 else '')

    def onTransitionIn(self):
    	bs.TeamGameActivity.onTransitionIn(self, music='RunAway')
    

    def onBegin(self):
        bs.TeamGameActivity.onBegin(self)

        self.setupStandardTimeLimit(self.settings['Time Limit'])
        self.setupStandardPowerupDrops()
 
    
        self._puckSpawnPos = self.getMap().getFlagPosition(None)
        self._spawnPuck()

        # set up the two score regions
        defs = self.getMap().defs
        self._scoreRegions = []
        self._scoreRegions.append(bs.NodeActor(bs.newNode("region",
                                                          attrs={'position':defs.boxes["goal1"][0:3],
                                                                 'scale':defs.boxes["goal1"][6:9],
                                                                 'type':"box",
                                                                 'materials':[self._scoreRegionMaterial]})))
        
        self._scoreRegions.append(bs.NodeActor(bs.newNode("region",
                                                          attrs={'position':defs.boxes["goal2"][0:3],
                                                                 'scale':defs.boxes["goal2"][6:9],
                                                                 'type':"box",
                                                                 'materials':[self._scoreRegionMaterial]})))
        self._updateScoreBoard()

        bs.playSound(self._chantSound)
    def spawnPlayer(self,player):
        spaz = self.spawnPlayerSpaz(player)
        spaz.connectControlsToPlayer()
        if self.settings["Speed"]: spaz.node.hockey = True
        if self.settings["Night Mode"]: bs.getSharedObject('globals').tint = (0.5,0.7,1)
        spaz.spazLight = bs.newNode('light',
                attrs={'position':(0,0,0),
                        'color':spaz.node.color,
                        'radius':0.10,
                        'intensity':1,
                        'volumeIntensityScale': 10.0})
                    
        spaz.node.connectAttr('position',spaz.spazLight,'position')
          
        def checkExistsSpaz():
            if spaz.node.exists():
                bs.gameTimer(10,bs.Call(checkExistsSpaz))
            else:
                spaz.spazLight.delete()
                
        checkExistsSpaz()
        

    def onTeamJoin(self,team):
        team.gameData['score'] = 0
        self._updateScoreBoard()
        

    def _handlePuckPlayerCollide(self):
        try:
            puckNode,playerNode = bs.getCollisionInfo('sourceNode','opposingNode')
            puck = puckNode.getDelegate()
            player = playerNode.getDelegate().getPlayer()
        except Exception: player = puck = None

        if player is not None and player.exists() and puck is not None: puck.lastPlayersToTouch[player.getTeam().getID()] = player

    def _killPuck(self):
        self._puck = None

    def _handleScore(self):
        """ a point has been scored """

        # our puck might stick around for a second or two
        # we dont want it to be able to score again
        if self._puck.scored: return

        region = bs.getCollisionInfo("sourceNode")
        for i in range(len(self._scoreRegions)):
            if region == self._scoreRegions[i].node:
                break;

        scoringTeam = None
        for team in self.teams:
            if team.getID() == i:
                scoringTeam = team
                team.gameData['score'] += 1

                # tell all players to celebrate
                for player in team.players:
                    try: player.actor.node.handleMessage('celebrate',1000)
                    except Exception: pass

                # if weve got the player from the scoring team that last touched us, give them points
                if scoringTeam.getID() in self._puck.lastPlayersToTouch and self._puck.lastPlayersToTouch[scoringTeam.getID()].exists():
                    self.scoreSet.playerScored(self._puck.lastPlayersToTouch[scoringTeam.getID()],100,bigMessage=True)

                # end game if we won
                if team.gameData['score'] >= self.settings['Score to Win']:
                    self.endGame()
                    
		bs.shakeCamera(intensity=0.0)
        bs.playSound(self._glSound)
        bs.playSound(self._cheerSound)

        self._puck.scored = True

        # kill the puck (it'll respawn itself shortly)
        bs.gameTimer(500,self._killPuck)
        
        self._updateScoreBoard()
        

    def endGame(self):
        results = bs.TeamGameResults()
        for t in self.teams: results.setTeamScore(t,t.gameData['score'])
        self.end(results=results)

    def _updateScoreBoard(self):
        """ update scoreboard and check for winners """
        winScore = self.settings['Score to Win']
        for team in self.teams:
            self._scoreBoard.setTeamValue(team,team.gameData['score'],winScore)

    def handleMessage(self,m):

        # respawn dead players if they're still in the game
        if isinstance(m,bs.PlayerSpazDeathMessage):
            bs.TeamGameActivity.handleMessage(self,m) # augment standard behavior
            self.respawnPlayer(m.spaz.getPlayer())
        # respawn dead pucks
        elif isinstance(m,PuckDeathMessage):
            if not self.hasEnded():
                bs.gameTimer(3000,self._spawnPuck)
        else:
            bs.TeamGameActivity.handleMessage(self,m)

    def _flashPuckSpawn(self):
        light = bs.newNode('light',
                           attrs={'position': self._puckSpawnPos,
                                  'heightAttenuated':False,
                                  'color': (1,0.2,0.6)})
        bs.animate(light,'intensity',{0:0,550:1,0:0},loop=True, offset=20)
        bs.gameTimer(500,light.delete)

    def _spawnPuck(self):
        bs.playSound(self._swipSound)
        bs.playSound(self._spwnSound)
        self._flashPuckSpawn()

        self._puck = Puck(position=self._puckSpawnPos)
        self._puck.scored = False
        self._puck.lastHoldingPlayer = None
        self._puck.light = bs.newNode('light',
                                      owner=self._puck.node,
                                      attrs={'intensity':0.3,
                                             'heightAttenuated':False,
                                             'radius':0.3,
                                             'color': (1,0,1)})
        self._puck.node.connectAttr('position',self._puck.light,'position')
 # #######WorkBySobyDamn#####
