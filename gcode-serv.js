var serialport = require('serialport', 
				{ 
				  baudrate: 57600,
				  dataBits: 8,
				  parity: 'none',
				  stopBits: 1
				});
var SerialPort = serialport.SerialPort;
var port = null;
var portname = "";

var tcport = 8080;
var express = require('express');
var app = express();
var http = require('http').Server(app);
var io = require('socket.io')(http);

var multer  =   require('multer');
var storage =   multer.diskStorage({
  destination: function (req, file, callback) {
    callback(null, 'ngc');
  },
  filename: function (req, file, callback) {
    callback(null, file.originalname);
  }
});
var fileFilter = function (req, file, cb) {
     if (file.originalname.indexOf('.ngc') != -1) {
       return cb(null, false, new Error('gcode files only, please!'));
     }
     cb(null, true);
   }
var limits = {fileSize: 5242880};
var upload = multer({ storage : storage}).single('gcode');

http.listen(tcport, function(){
  console.log('websocket open on *:' + tcport);
});

io.on('connection', function(socket){
  socket.on('gcode', function(msg){
    console.log('message: ' + msg);
    q.push(msg);
  });
});

app.use('/', express.static(__dirname + '/www')); // redirect root
app.use('/js', express.static(__dirname + '/www/js')); // redirect static JS
app.use('/css', express.static(__dirname + '/www/css')); // redirect static CSS
app.use('/js', express.static(__dirname + '/node_modules/bootstrap/dist/js')); // redirect bootstrap JS
app.use('/fonts', express.static(__dirname + '/node_modules/bootstrap/dist/fonts')); // redirect bootstrap JS
app.use('/js', express.static(__dirname + '/node_modules/jquery/dist')); // redirect JS jQuery
app.use('/js', express.static(__dirname + '/node_modules/socket.io/node_modules/socket.io-client')); // redirect JS jQuery
app.use('/js', express.static(__dirname + '/node_modules/angular')); // redirect JS jQuery
app.use('/css', express.static(__dirname + '/node_modules/bootstrap/dist/css')); // redirect CSS bootstrap
app.use('/ngc', express.static(__dirname + '/ngc')); // redirect CSS bootstrap

var fs = require('fs');
var moment = require('moment');

app.get('/api/files/list',function(req,res){
  fs.readdir('ngc/', function(err, files) {
    filejson = '{"files":[\n';
    files.forEach(function (file) {
      if (file.indexOf('.ngc') != -1) {
        //console.log(file);

        var stats = fs.statSync("ngc/" + file);
        //var fileSize = formatBytes(stats["size"]);
        var fileSize = stats["size"];
        var fileDate = moment(stats["mtime"]).fromNow();

        filejson += '{"name": "' + file + '", "size":' + fileSize + ', "date":"' + fileDate  + '"},\n';
      }
    });  
    filejson = filejson.substring(0, filejson.length - 2);
    filejson += "\n]}";
    res.send(filejson);  
  });
});

function formatBytes(bytes,decimals) {
   if(bytes == 0) return '0 Byte';
   var k = 1000; // or 1024 for binary
   var dm = decimals + 1 || 3;
   var sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
   var i = Math.floor(Math.log(bytes) / Math.log(k));
   return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

app.get('/api/files/unlink/:fname', function(req,res){
  fs.unlink('ngc/' + req.params.fname, function(exists){
    res.send( !exists ? '{"status": 1, "msg": "file deleted"}' : '{"status": 0, "msg": "file does not exist"}' );
  });
});

app.post('/api/files/upload',function(req,res){
    upload(req,res,function(err) {
        res.send( err ? '{"status": 0, "msg": "' + err + '"}' : '{"status": 1, "msg": "file uploaded"}' );
    });
});

app.get('/api/serial/list',function(req,res){
  if( port != null && port.isOpen() ) { //serialport.isOpen() ) {
    res.send(' {"sstatus": 1, "ports": []} ');
  } else {

    var portlist = "";
    serialport.list(function (err, ports) {
      portlist += '{\n"sstatus": 0, \n"ports": [';
      ports.forEach(function(port) {
        portlist += '{"name": "' + port.comName + '",';
        portlist += '"pnpid": "' + port.pnpId + '",';
        portlist += '"manuf": "' + port.manufacturer + '"}, \n';
      });
      portlist = portlist.substring(0, portlist.length - 3);
      portlist += ']}';
      res.send(portlist);
    });

  }
});

app.get('/api/serial/gcode/:gcode', function(req, res) {
  var param_string = req.params.gcode;

  if( param_string.substring(0, 3) == 'G0 ' ) {

    q.push('G91');
    q.push(param_string);
    q.push('G90');
    res.send("gcode is set to " + req.params.gcode);
  } else {

    q.push(param_string);
    res.send("gcode is set to " + req.params.gcode);
  }

});

app.get('/api/serial/close', function(req, res) {
  if( port != null && port.isOpen() ){
    port.close();
    res.send( '{"status": 1, "msg": "port closed"}' );
  } else {
    res.send( '{"status": 0, "msg": "no open ports"}' );
  }
});

app.get('/api/serial/conn/:sp', function(req, res) {
  port = new SerialPort('/dev/' + req.params.sp, {
    parser: serialport.parsers.readline('\n')
  }, function() {
    io.emit('gcode', 'connected to /dev/' + req.params.sp);
    portname = '/dev/' + req.params.sp;
    port.on('data', function (data) {
      console.log(data);
      io.emit('gcode', data.trim());
      if( !q.empty() && q.print_status != 2 ) {
          comm( q.shift() );
      }
    });
    res.send('{"status": 1, "msg": "Serial connected"}');
  });
});

function comm (com) {
  console.log(com);
  port.write(com + "\n", function () {
    port.drain(function() {});
  });
}

var printQue = require("./print-que.js");
var q = new printQue();

app.get('/api/print/start/:file', function(req, res) {
  q.print(req.params.file);
});

app.get('/api/print/stop/', function(req, res) {
  q.stop();
});

app.get('/api/print/pause/', function(req, res) {
  q.pause();
});

app.get('/api/print/list/', function(req, res) {
  var printjson = '{\n';
  
  printjson += '"pstatus": ' + q.print_status + ',\n';
  printjson += '"file": "' + q.current_file + '",\n';
  printjson += '"progress": ' + q.progress() + '\n';

  printjson += '}';
  res.send(printjson);
});
