import threading
import datetime
from database import database
import pytz
import sys
import threading
import pickle
import ConfigParser, os
from tasks import tasks
import base64

class Agent:
    def __init__(self, config_file):
        config = ConfigParser.ConfigParser()
        config.readfp(open('config.txt'))
        self.db_name = config.get("Agent", "database")
        self.db = database.Database(self.db_name) 
        self.wake_interval = int(config.get("Agent", "wake_every"))
        self.stopwords = open(config.get("Agent", "stop_words"), 'r').read().split()
        self.local_timezone = pytz.timezone ("America/New_York")
        self.woke_at = self.utc_for(datetime.datetime.now())
        self.tasks = [tasks.Task]
        self.tweet_cache = []
        self.streamSampler = Streamer(0,self,config.get("Stream", "username"),config.get("Stream", "password"))
        self.filterSampler = Streamer(0,self,config.get("FilterStream", "username"),config.get("FilterStream", "password"))
    
    def utc_for(self, dt):
        local_dt = dt.replace (tzinfo = self.local_timezone)
        return local_dt.astimezone(pytz.utc)        
        
    def wake(self):
        print "Wake"
        self.db = database.Database(self.db_name)
        try:
            self.woke_at = self.utc_for(datetime.datetime.now())
            self.process_tasks()
            threading.Timer(self.wake_interval, self.wake).start()
        except Exception as ex:
            print "Unexpected error:", sys.exc_info()[0]
       	    print ex.args
            print ex 

        self.db.commit()
        self.db.close()
        self.db = None
            
    ###############################################################
    ## Blackbaord
    ## For tasks to store data in
    ## 

    def stash(key, obj):
        pass
    
    def fetch(key):
        pass
    
    def destroy(key):
        pass
        
    ###############################################################
    ## Task Processing
    ## Ideally this would be nicely split out into separate code files
    ## but for the time being it will all be globbed into this function

    def unfinished_tasks(self):
        sql = "SELECT tid, task, after, reschedule, delta, args FROM tasks WHERE complete = 0 AND after < ?"
        params = (datetime.datetime.now())
        cur = self.db.query(sql, params)
        res = []
        for row in cur:
            res.append([row[0], row[1], row[2], row[3], row[4], row[5]])
        cur.close()
        return res

    def process_tasks(self):
        for task in self.unfinished_tasks():
            self.process_task(task)

    def process_task(self, task):
        gotit = False
        for taskType in self.tasks:
            if (taskType.taskName == task[1]):
                gotit = True
                taskImpl = taskType(self, pickle.loads(base64.b64decode(task[5])))
                if task[3] == 1:
                    taskImpl.reschedules = True
                else:
                    taskImpl.reschedules = False
                    
                taskImpl.execute()
                taskImpl.complete()
        if not gotit:
            print "Unknown Task"
            print task
    
    def receive_tweet(self, tweet):
        self.tweet_cache.append(tweet)
    
    def save_tweets(self, tweet):
        tweets = self.tweet_cache
        self.tweet_cache = []
        print "[%s] Saving %d Tweets" % (str(datetime.datetime.now()), len(tweets))
        for tweet in tweets:
            self.db.save_tweet(tweet)
    
def main():
    agent = Agent("config.txt")
    # task = tasks.Task(agent.db)
    # task.schedule(False)
    agent.wake()

if __name__ == "__main__":
    main()
    

