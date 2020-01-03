from __future__ import division
import threading
import json
import os
import urllib2
# where our stats file and pretty html output will go
statsfile = '/var/www/html/stats.json'
htmlfile = '/var/www/html/index.html'
rank = '/home/osum/pub2/data/scripts/topranks.py'
def update(score_set):
     """
    Given a Session's ScoreSet, tallies per-account kills
    and passes them to a background thread to process and
    store.
    """ 
    # look at score-set entries to tally per-account kills for this round
     account_kills = {}
     account_killed = {}
     account_scores = {}
     account_played = {}
     account_name = {}
     account_localname = {}
     for p_entry in score_set.getValidPlayers().values():
        account_id = p_entry.getPlayer().get_account_id()
        if account_id is not None:
            account_kills.setdefault(account_id, 0)
            account_kills[account_id] += p_entry.accumKillCount
            account_killed.setdefault(account_id, 0)
            account_killed[account_id] += p_entry.accumKilledCount
            account_scores.setdefault(account_id, 0)
            account_scores[account_id] += p_entry.accumScore
            account_played.setdefault(account_id, 0)
            account_played[account_id] += 1
            account_localname.setdefault(account_id, p_entry.name)
            account_localname[account_id] = p_entry.name
    # Ok; now we've got a dict of account-ids and kills.
    # Now lets kick off a background thread to load existing scores
    # from disk, do display-string lookups for accounts that need them,
    # and write everything back to disk (along with a pretty html version)
    # We use a background thread so our server doesn't hitch while doing this.
     UpdateThread(account_kills,account_killed,account_scores,account_played,account_name, account_localname).start()
class UpdateThread(threading.Thread):
    def __init__(self, account_kills, account_killed, account_scores, account_played, account_name, account_localname):
        threading.Thread.__init__(self)
        self._account_kills = account_kills
        self._account_killed = account_killed
        self._account_scores = account_scores
        self._account_played = account_played
        self._account_name = account_name
        self._account_localname = account_localname
    def run(self):
        # pull our existing stats from disk
        if os.path.exists(statsfile):
            with open(statsfile) as f:
                stats = json.loads(f.read())
        else:
            stats = {}
            
        # now add this batch of kills to our persistant stats
        for account_id, kill_count in self._account_kills.items():
            # add a new entry for any accounts that dont have one
            if account_id not in stats:
                # also lets ask the master-server for their account-display-str.
                # (we only do this when first creating the entry to save time,
                # though it may be smart to refresh it periodically since
                # it may change)
                url = 'http://bombsquadgame.com/accountquery?id=' + account_id
                response = json.loads(
                    urllib2.urlopen(urllib2.Request(url)).read())
                name_html = response['name_html']
                stats[account_id] = {'kills': 0, 'killed': 0, 'scores': 0, 'played': 0, 'name_html': name_html, 'account_id': account_id}
            # now increment their kills whether they were already there or not
            stats[account_id]['kills'] += kill_count
        for account_id, killed_count in self._account_killed.items():
            stats[account_id]['killed'] += killed_count
        for account_id, scores_count in self._account_scores.items():
            stats[account_id]['scores'] += scores_count
        for account_id, played_count in self._account_played.items():
            stats[account_id]['played'] += played_count
        for account_id, name in self._account_localname.items():
            stats[account_id]['localname'] = name
        # dump our stats back to disk
        with open(statsfile, 'w') as f:
            f.write(json.dumps(stats))
        # lastly, write a pretty html version.
        # our stats url could point at something like this...
        entries = [(a['scores'], a['kills'], a['killed'], a['played'], a['name_html'], a['localname'], a['account_id']) for a in stats.values()]
        # this gives us a list of kills/names sorted high-to-low
        entries.sort(reverse=True)
        with open(htmlfile, 'w') as f:
            f.write('<html lang="en"><head>\n<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script>\n<script type="text/javascript" src="blogsdata.json"></script><script type="text/javascript" src="BlogsUpdate.js"></script><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial scale=1"/><link rel="stylesheet" href="https://www.w3schools.com/lib/w3.css"/><link rel="stylesheet" href="osumstyle.css"/><title>#OSUM Players Stats</title></head><body onload="load()" class="background"><center><img src="logo1.png" WIDTH=350 HEIGHT=110 align="middle"></center><div class="dropdown"> <button class="dropbtn" style="margin-right:16px"><b>Join ▾</b></button><div class="dropdown-content"><a href="https://discord.gg/p86ag6g">Discord</a><a href="https://chat.whatsapp.com/LP1vMU8jgFvDwEnj3zpFYw">WhatsApp</a><a href="https://www.youtube.com/channel/UCAP2xSmi0WhXDs9ivpo1EAw">YouTube</a></div></div><div class="dropdown"><button class="dropbtn" style="margin-right:16px"><b>Help ▾</b></button><div class="dropdown-content"><a href="http://osum.ml/help">FAQs</a><a href="https://www.osum-blogs.ml/?m=1">Visit Blogs!</a><a href="http://osum.ml/ban">Banned Players!</a></div></div><div id= "blogsdata"></div><br><b><p style="line-height:1%" id="counter" class="counter"></p></b><table class="background" id="rankList"><tr><th><u>Rank</u></th><th><u>Player</u></th><th class="block"><u>Avg<br>Score</u></th><th class="block"><u>K/D</u></th><th class="block"><u>Death</u></th><th class="block"><u>Kill</u></th><th><u>Scores</u></th></tr>\n')
            for entry in entries:
            	scores = str(entry[0])
                kills = str(entry[1])
                killed = str(entry[2])
                gameplayed = str(entry[3])
                if int(entry[2]) <= 0:
                	kill_death_ratio = str(entry[1])
                else:
                	x = str(round(int(entry[1]) / int(entry[2]), 2))
                	kill_death_ratio = x
                num_scores = int(entry[0])
                num_played = int(entry[3])
                x = str(round(num_scores / num_played, 2))
                avgScore = x
                account_id = entry[6].encode('utf-8')
                name = entry[4].encode('utf-8')
                localname = entry[5].encode('utf-8')
                f.write('<tr><td><b>#</b></td>' '<td>' '<div class="modal" id="' + account_id + '" aria-hidden="true"><div class="wrap">' '<a href="#' + account_id + '">' + name + '</a></div>' '<div class="modal-dialog"><div class="modal-header"><h2>' '<a href="http://bombsquadgame.com/scores#profile?id=' + account_id + '">' + name + '</a>' '<a href="#home" class="btn-close" aria-hidden="true">×</a></div>' '<div class="modal-body"><div class="column"><p class="profile"><font size="1px">Last name used</font><br>' + localname + '<br><br><font size="1px">Total Score</font><br>' + scores + '<br><br>' '<font size="1px">Kills</font><br>' + kills + '</p></div>' '<div class="column"><p class="profile"><font size="1px">Deaths</font><br>' + killed + '<br><br><font size="1px">Total Game Played</font><br>' + gameplayed + '</p></div><hr />' '<div class="column"><p><font size="3px"><b>Average Score</b></font><br>' + avgScore + '</div>' '<div class="column"><p><font size="3px"><b>Kill/Death</b></font><br>' + kill_death_ratio + '</div><hr /><div class="modal-footer"><a href="#home" style="background: #ffb84d; border: #ffb84d; border-radius: 8px; color: black; display: inline-block; font-size: 14px; padding: 8px 15px; text-decoration: none; text-align: center; min-width: 60px; position: relative; transition: color .1s ease;">Close</a></div></div></div></div></p>' '</td>' '<td class="blocked">' + avgScore + '</td>' '<td class="blocked">' + kill_death_ratio +  '</td>' '<td class="blocked">' + killed +  '</td>' '<td class="blocked">' + kills +  '</td>' '<td>' + scores +  '</td>\n')
            f.write('</table><script src="timer.js"></script><script src="addons.js"></script></body></html>')
            
        print 'Scores and Data Updated!'
        with open(rank, 'w') as f:
            f.write("player = [")
            for entry in entries:
            	a = str(entry[6])
            	f.write(" '" + a + "',")
            f.write("]\n")
            f.write("admin = ['pb-IF4RV1QiHA==']\n")
            f.write("iadmin = ['pb-IF4iU3YY','pb-IF4nV1YoJg==']\n")
            f.write("topone = player[:1]\n")
            f.write("topthree = player[:3]\n")
            f.write("topten = player[:10]\n")
            
        print 'Ranks Updated'
