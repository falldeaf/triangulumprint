var method = printQue.prototype;

function printQue() {
  this.que = [];
  this.print_status = 0; //0 = inactive, 1 = printing, 2 = paused
  this.total_steps = 0;
  this.current_file = "";
}

method.empty = function() {
  return (this.que.length > 0) ? false : true;
};

method.push = function(code) {
  this.que.push(code);
};

method.shift = function() {
  return this.que.shift();
};

method.print = function(file) {
  if( fileCheck(file) ) {
    this.print_status = 1;
    this.current_file = file;
    var fs = require('fs');
    var array = fs.readFileSync('file.txt').toString().split("\n");
    this.total_steps = array.length;
    this.que = array;
  }
};

method.cancelPrint = function() {
  this.print_status = 0;
  this.que = [];
};

method.progress = function() {
  if(this.print_status == 0) return 0;

  return Math.round( ( (this.que.length - this.total_steps ) / this.total_steps ) * 100 );
}

method.togglePause = function() {
  switch(this.print_status) {
    case 0:
      break;
    case 1:
      this.print_status = 2;
      break;
    case 2:
      this.print_status = 1;
      break;
  }
};

method.fileCheck = function(file) {
  var fs = require('fs');

  fs.exists(file, function(exists) {
    if (exists) {
      return true;
    } else {
      return false;
    }
  });
};

module.exports = printQue;
