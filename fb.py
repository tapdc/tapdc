'''
NOTES:
-it's basically impossible to maintain a "User Token" indefinitely
 -they expire in 1 hour
 -they require user interaction to renew
  -a "secret" is embedded in the form dialog, which needs to be submitted
   to convert oauth to complete the request successfully. you could probably
   dig it out, but it would take some work
  -for reference, the URL is:
   https://www.facebook.com/v2.3/dialog/oauth?response_type=token&display=popup&client_id=145634995501895&redirect_uri=https%3A%2F%2Fdevelopers.facebook.com%2Ftools%2Fexplorer%2Fcallback%3Fmethod%3DGET%26path%3DTaiwaneseAmericanProfessionalsDC%252Fevents%26&scope=user_posts%2Cmanage_pages
   -"scope" lists the rights requested

-you can't access the Graph API anonymously. apparently you could long
 ago but they disabled it
 -http://stackoverflow.com/questions/7633234/get-public-page-statuses-using-facebook-graph-api-without-access-token

-per the above site, it's best to use a "Client Token" from an App
 -the process to get a client token is not well document
 -App > Settings > Advanced > Client Token is the WRONG token and will not work
 -the correct way to do it is:
  https://graph.facebook.com/oauth/access_token?client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&grant_type=client_credentials
 -note: you will need your FB password to retreive the secret from your app
 -this yields a client token that i'm pretty sure never expires

'''

import re
import sys
import time
import json
import urllib2
import sqlite3

#the client token
token = '1825743310990639|ges2quVkdhVB8Dpz9jG6C2qQe8A' #<--put your token here, or specify as argv[1]

cache = sqlite3.connect('cache.db')
cache.execute('CREATE TABLE IF NOT EXISTS cache (url UNIQUE, t, data)')

def req(url,max_age=3600):
	
	now = int(time.time())
	r = cache.execute('SELECT t,data FROM cache WHERE url = ?',(url,)).fetchall()
	if r:
		t,data = r[0]
		if (now-t)<max_age:
			open('last.json','w').write(data)
			return json.loads(data)
	
	try:
		r = urllib2.urlopen(url)
		r = r.read()
		
		open('last.json','w').write(r)
		cache.execute('REPLACE INTO cache VALUES (?,?,?)',(url,now,r))
		cache.commit()
		
		return json.loads(r)
		
	except urllib2.HTTPError as e:
		r = e.read()
		print r
		print url
		raise

def fb(path):
	if '?' not in path:
		path += '?'
	else:
		path += '&'
	return req('https://graph.facebook.com/v2.4/'+path+'access_token='+token)

class Event:
	'''
	id
	name
	start_time
	end_time
	link
	description
	place
	address
	latlng
	cover
	past
	'''
	def __init__(self,d):
		self.id = int(d['id'])
		self.name = d['name']
		self.start_time = self.parse_time(d['start_time'])
		if 'end_time' in d:
			self.end_time = self.parse_time(d['end_time'])
		else:
			self.end_time = 0
		
		now = int(time.time())
		self.past = False
		if self.end_time and self.end_time<now:
			self.past = True
		elif (self.start_time+7200)<now:
			self.past = True
		
		self.link = 'https://www.facebook.com/events/'+str(self.id)
	
	@staticmethod
	def parse_time(x):
		try:
			ts = time.strptime(x[:19],'%Y-%m-%dT%H:%M:%S')
			return time.mktime(ts)
		except:
			print x
			ts = time.strptime(x[:10],'%Y-%m-%d')
			return time.mktime(ts)
	
	def load(self):
		r = fb(str(self.id)+'?fields=cover,place,description')
		self.description = r['description']
		
		if 'place' in r:
		
			self.place = r['place']['name']
			
			if 'location' in r['place']:
				loc = r['place']['location']
				
				self.address =''
				if 'street' in loc:
					self.address += loc['street']
				else:
					self.address += self.name
				
				if 'city' in loc and 'state' in loc:
					self.address += ', '+loc['city']+', '+loc['state']
				
				self.latlng = (loc['latitude'],loc['longitude'])
			else:
				self.address = self.place
				self.latlng = None
			
		else:
			self.place = 'Unknown Location'
			self.address = None
			self.latlng = None
		
		if 'cover' in r:
			self.cover = r['cover']['source']
		else:
			self.cover = None
	
	def format_time(self):
		ts = time.localtime(self.start_time)
		s = time.strftime('%A %B',ts)
		s += ' '+str(int(time.strftime('%d',ts)))
		h1 = ts.tm_hour
		if h1==0:
			return s
		
		s += ', '
		p1 = 'AM'
		if h1>=12:
			p1 = 'PM'
			if h1>12:
				h1 -= 12
		h1 = str(h1)
		m1 = ''
		if ts.tm_min:
			m1 = ':%02d'%(ts.tm_min)
		
		if self.end_time:
			ts = time.localtime(self.end_time)
			p2 = 'AM'
			h2 = ts.tm_hour
			if h2>=12:
				p2 = 'PM'
				if h2>12:
					h2 -= 12
			h2 = str(h2)
			m2 = ''
			if ts.tm_min:
				m2 = ':%02d'%(ts.tm_min)
			
			s += h1+m1
			if p1!=p2:
				s += ' '+p1
			s += '-'
			s += h2+m2+' '+p2
			
		else:
			s += h1+m1+' '+p1
		
		return s
	
	def month(self):
		ts = time.localtime(self.start_time)
		s = time.strftime('%b',ts)
		return s
	
	def date(self):
		ts = time.localtime(self.start_time)
		s = time.strftime('%d',ts)
		return s
	
	def preview_time(self):
		ts = time.localtime(self.start_time)
		s = time.strftime('%A %B ',ts)+str(int(time.strftime('%d',ts)))
		return s

	def __str__(self):
		return self.name+' '+self.format_time()

	def html_preview(self):
		html = ''
		html += '<div class="event_preview">'
		html += '<b>Next Event:</b>'
		html += '<a href="/events.html">'
		
		if self.cover:
			html += '<div class="summary" style="background-image:url('+self.cover+');">'
		else:
			html += '<div class="summary">'
		
		html += '<h1>'+self.name+'</h1>'
		html += '<p>'
		html += '<span class="time">'+self.format_time()+'</time>'
		html += '</p>'
		
		html += '</div>'
		
		html += '</a>'
		html += '</div>'
		return html.encode('utf8')
	
	def html(self):
		html = ''
		
		if not self.past:
			html += '<div class="event upcoming">'
		else:
			html += '<div class="event">'
		
		html += '<a href="javascript:void(0);" onclick="event_toggle(this)">'
		if self.cover:
			html += '<div class="summary" style="background-image:url('+self.cover+');">'
		else:
			html += '<div class="summary">'
		
		html += '<h1>'+self.name+'</h1>'
		html += '<p>'
		html += '<span class="time">'+self.format_time()+'</time>'
		html += ' &bull; '
		html += '<span>'+self.place+'</span>'
		html += '</p>'
		
		html += '</div>'
		html += '</a>'
		
		html += '<div class="details">'
		html += '<table>'
		html += '<tbody>'
		html += '<tr><td>'
		
		if self.address and not self.latlng:
			html += '<p class="address"><a href="http://maps.apple.com/?q='+self.address.replace(' ','+')+'" target="_blank">'+self.address+'</a></p>'
		
		#parse links in description for convenience,
		# but also so we can break them in CSS so they don't push the map out of the table
		desc = self.description
		desc = re.sub('(https?://[^\\s]+)','<a href="\\1">\\1</a>',desc)
		
		#convert newlines to html
		desc = desc.replace('\n','<br>')
		
		#split long words so map isn't pushed off screen
		#ex: 49 ~'s 
		#note: a span with style="word-break:break-all" doesn't work
		desc = re.sub('([^\\s<>\\.\\-/\\d&=\\?,]{30})','\\1 ',desc)
		
		html += '<p class="description">'+desc+'</p>'
		html += '<p class="fb"><a href="'+self.link+'" target="_blank"><i class="fa fa-facebook-square" style="color:rgb(65,94,155);"></i> View on Facebook</a></p>'
		
		if self.latlng:
			html += '</td><td>'
			html += '<div class="map" data-lat="'+str(self.latlng[0])+'" data-lon="'+str(self.latlng[1])+'"></div>'
			if self.address:
				html += '<p class="address" style="text-align:center"><a href="http://maps.apple.com/?q='+self.address.replace(' ','+')+'" target="_blank">'+self.address+'</a></p>'
		
		html += '</td></tr>'
		html += '</tbody>'
		html += '</table>'
		html += '</div>'
		
		html += '</div>'
		
		return html.encode('utf8')
	
if __name__=='__main__':
	
	if len(sys.argv)>1:
		token = sys.argv[1]
	
	print 'Getting events...'
	#get 2 pages of events
	events = []
	since = str(int(time.time())-24*3600*31*6) #past 6 months
	r = fb('TaiwaneseAmericanProfessionalsDC/events?since='+since)
	for d in r['data']:
		e = Event(d)
		e.load()
		events.append(e)
	
	events.sort(key=lambda x: -x.start_time)

	# for e in events:
	# 	print str(e)
	print len(events),'events'
	
	now = int(time.time())
	upcoming_events = []
	past_events = []
	
	latest_upcoming = None
	for e in events:
		if not e.past:
			upcoming_events.append(e.html())
			latest_upcoming = e
		else:
			past_events.append(e.html())
	
	upcoming_events.reverse()
	upcoming_events = ''.join(upcoming_events)
	past_events = ''.join(past_events)
	
	if not upcoming_events:
		upcoming_events = '<div style="text-align:center;margin-top:50px;">No upcoming events :\'(</div>'
	if not past_events:
		past_events = '<div style="text-align:center;">No past events.</div>'
	
	open('www/_upcoming.html','wb').write(upcoming_events)
	open('www/_past.html','wb').write(past_events)
	
	if latest_upcoming:
		html = latest_upcoming.html_preview()
	else:
		html = '<div style="text-align:center;margin-top:10px;">'
		html += '<i class="fa fa-frown-o"></i> <span style="font-style:italic;">No upcoming events &mdash; Stay tuned!</span>'
		html += '<div style="margin-top:10px;"><a href="/events.html">View Past Events</a></div>'
		html +='</div>'
	open('www/_next.html','wb').write(html)
	
	

