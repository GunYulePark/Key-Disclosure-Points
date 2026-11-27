import http from 'node:http';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const devPreview=process.argv.includes('--dev-preview');
const docs=path.resolve(fileURLToPath(new URL(devPreview?'../.local/case-preview/site':'../docs',import.meta.url)));
const base='/Key-Disclosure-Points/';
const port=devPreview?4175:4174;
http.createServer(async(req,res)=>{
 const pathname=new URL(req.url,'http://127.0.0.1').pathname;
 if(pathname==='/'){res.writeHead(302,{Location:base});res.end();return;}
 if(!pathname.startsWith(base)){res.writeHead(404);res.end();return;}
 const relative=decodeURIComponent(pathname.slice(base.length))||'index.html';
 const file=path.resolve(docs,relative);
 if(!file.startsWith(docs+path.sep)){res.writeHead(403);res.end();return;}
 try{const body=await readFile(file);res.writeHead(200,{'Content-Type':({'.js':'text/javascript','.css':'text/css','.html':'text/html; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'}[path.extname(file)]||'application/octet-stream')});res.end(body);}catch{res.writeHead(404);res.end();}
}).listen(port,'127.0.0.1',()=>console.log('Local: http://127.0.0.1:'+port+base));
