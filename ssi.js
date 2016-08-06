//static file server that supports server-side includes
//-support etags and max-age
//-caches templates on server-side
//-simple logging

var config = {
	port : 80,
	root : 'www',
	maxage : 3600,
	server : 'AaronSSI/1',
	cachemaxage : 600,
	maxlogsize : 100*1000,
	auth : 'tap:asdf',
	fb_token : ''
};

var fs = require('fs');
var http = require('http');
var child_process = require('child_process');

//load config from config.json if specified
try{
	var _config = JSON.parse(fs.readFileSync('config.json'));
	Object.assign(config,_config);
	console.log('Configuration loaded from config.json');
}
catch(e){}

//template cache of path => { headers:headers, html:html, time:time }
//uses config.cachemaxage (max age in seconds)
var cache = {};

//periodically check log and rename if too big
setInterval(function(){
	fs.stat('log',function(err,stats){
		if(stats && stats.size>config.maxlogsize){
			//will overwrite without throwing
			fs.rename('log','log.1');
		}
	});
},600*1000); //every 10 minutes

function content_type(path){
	var ext = path.substr(path.lastIndexOf('.')+1);
	//console.log(ext+" file");
	var o = {
		//text types
		'html' : 'text/html',
		'css' : 'text/css',
		'js' : 'application/javascript',
		
		//image types
		'gif' : 'image/gif',
		'jpeg' : 'image/jpeg',
		'jpg' : 'image/jpeg',
		'png' : 'image/png',
		'svg' : 'image/svg+xml',
		'ico' :  'image/x-icon',
		
		//binary types
		'gz' : 'application/x-gzip',
		'mp3' : 'audio/mpeg',
		'pdf' : 'application/pdf',
		'zip' : 'application/zip',
		
		//video types
		'avi' : 'video/mpeg',
		'mov' : 'video/quicktime',
		'mp4' : 'video/mp4',
	};
	if(o[ext]) return o[ext];
	
	//for everthing else, make the browser display it
	return 'text/plain';
}

//my version of server-side includes
//ex: <!--#include /template.html some_name="Some Value"-->
//-becomes template.html except $some_name becomes "Some Value"
function render(path,context){
	var html = String(fs.readFileSync(path));
	var folder = path.slice(0,path.lastIndexOf('/'));
	html = html.replace(/<!--#include ([^\s]+?)(\s.+?)?-->/g,function(tag,name,args){
		var r = /([^\s=]+)="([^"]+)"/g;
		var m;
		var o = {};
		while(m = r.exec(args)){
			var k = m[1];
			var v = m[2];
			o[k] = v;
		}
		try{
			var sub_path = name[0]=='/'?config.root+name:folder+'/'+name;
			var sub_html = String(fs.readFileSync(sub_path));
			sub_html = sub_html.replace(/\$([\w_]+)/g,function(variable,name){
				if(name in o) return o[name];
				return variable;
			});
			return sub_html;
		}
		catch(e){
			console.log('Missing: '+sub_path);
			return tag;
		}
	});
	if(context){
		html = html.replace(/\$([\w_]+)/g,function(variable,name){
			if(name in context) return context[name];
			return variable;
		});
	}
	return html;
}

function log(req,res){
	//log request
	//var time = (new Date()).toUTCString();
	var time = Math.floor((new Date()).getTime()/1000);
	var status = res.statusCode;
	var path = req.url;
	
	//this can happen if client disconnects before we get here
	if(!req.connection.remoteAddress) var ip = 'DISCONNECTED';
	else var ip = req.connection.remoteAddress.replace('::ffff:','');
	var ref = req.headers['referer'];
	var ua = req.headers['user-agent'];
	fs.appendFile('log',JSON.stringify([time,status,path,ip,ref,ua])+'\n');
}

function serve(req,res){
	
	//don't allow relative paths
	if(req.url.match(/(^\.|\.\.)/)){
		res.writeHead(200,{'Content-Type':'text/plain'});
		res.end("404 Not Found");
		return;
	}
	
	//special case for log
	//check auth and display in reverse order
	if(req.url=='/log'){
		
		//check auth if specified
		if(config.auth){
			var passed = false;
			var auth = req.headers['authorization'];
			if(auth && auth.match(/^Basic /)){
				auth = Buffer(auth.slice(6),'base64').toString();
				if(auth==config.auth){
					passed = true;
				}
			}
			if(!passed){
				res.writeHead(401,{'WWW-Authenticate':'Basic realm=""'});
				res.end('Unauthorized. Please authenticate.');
				return;
			}
		}
		
		var data = fs.readFileSync('log').toString();
		data = log.trim().split('\n').reverse().join('\n');
		res.writeHead(200,{'Content-Type':'text/plain'});
		res.end(data);
		return;
	}
	
	//get absolute path
	var path = config.root+req.url;
	if(req.url=='/') path = config.root+'/index.html';
	
	//look in cache
	var item = cache[path];
	if(item){
		var age = Math.floor((new Date()).getTime()/1000)-item.time;
		if(age<=config.cachemaxage){
			res.writeHead(200,item.headers);
			res.end(item.html);
			return;
		}
		//if expired, fall through
	}
	
	//look for file
	fs.stat(path,function(err,stats){
		if(stats && stats.isFile()){
			var ct = content_type(path);
			var headers = {
				'Content-Type': ct ,
				'Cache-Control': 'max-age='+config.maxage,
				'Server': config.server
			};
			
			//templates
			if(ct=='text/html'){
				var html = render(path);
				res.writeHead(200,headers);
				res.end(html);
				
				//store in cache
				cache[path] = {
					html: html,
					headers: headers,
					time: Math.floor((new Date()).getTime()/1000)
				};
				
				//log it
				log(req,res);
			}
			
			//static files
			else{
				//support etags
				var server_etag = '"'+stats.mtime.getTime().toString(16)+'"';
				var client_etag = req.headers['if-none-match'];
				
				//if cached by client
				if(client_etag==server_etag){
					res.writeHead(304);
					res.end();
				}
				
				//send whole file if not cached by client
				else{
					headers['ETag'] = server_etag;
					headers['Content-Length'] = stats.size;
					res.writeHead(200,headers);
					fs.createReadStream(path,{bufferSize: 4096}).pipe(res);
				}
			}
		}
		else{
			res.writeHead(200,{'Content-Type':'text/plain'});
			res.end("404 Not Found");
			log(req,res);
		}
	});
}

http.createServer(serve).listen(config.port);
console.log('Listening on port '+config.port);

//start python bot
function run_bot(){
	console.log('Running bot...')
	child_process.exec('python fb.py "'+config.fb_token+'"',function(e,out,err){
		console.log(out);
		console.log(err);
	});
}
run_bot();
setInterval(run_bot,3600*1000);

