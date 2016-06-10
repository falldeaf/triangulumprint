function gcodeVis(cvs, filestring) {
    this.canvas = cvs;
    this.printing_begun = false;
    this.c=document.getElementById(this.canvas);
    this.ctx=this.c.getContext("2d");
    this.lines = filestring.split('\n');
    this.pen = false;
    this.last_position = {x: 0, y: 0};
    this.last_line_number = 0;

    this.xoff = 250;
    this.yoff = -250;
    this.xvalence = 1;
    this.yvalence = -1;
    this.resize = .5;

    this.total_distance = 0;
}

gcodeVis.prototype.render = function(color) {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    this.ctx.beginPath();
    this.ctx.moveTo(0,0);

    for(var line = 0; line < this.lines.length; line++){
        this.nextLine(line);
    }

    this.ctx.strokeStyle = '#' + color;
    this.ctx.stroke();
    
    //alert(this.total_distance);
}

gcodeVis.prototype.ptime = function() {
    return this.total_distance;
}

gcodeVis.prototype.progress = function(current_line_number) {
	if(!this.printing_begun) {
    	this.printing_begun = true;
        this.render("eaeaea");
    }

	if(current_line_number > 0 && current_line_number > this.last_line_number) {
        this.ctx.beginPath();

	    //this.ctx.moveTo(this.last_position.x,this.last_position.y);
        for(var line = this.last_line_number; line < current_line_number; line++){
            this.nextLine(line);
        }

		this.ctx.strokeStyle = '#4bff05';
        this.ctx.stroke();
        
        this.line_number = current_line_number;
    }
}

gcodeVis.prototype.nextLine = function(index) {
    var comm = this.lines[index].split(' ');
    if(comm[0] == 'G00') {

        if(comm[1].charAt(0) == 'X') {
            var x = ((parseFloat(comm[1].substring(1)) + this.xoff) * this.xvalence) * this.resize;
            var y = ((parseFloat(comm[2].substring(1)) + this.yoff) * this.yvalence) * this.resize;
            
            if(this.pen) {
                this.ctx.lineTo( x, y );
            } else {
                this.ctx.moveTo( x, y );
            }
            //find distance and add to total
            this.total_distance += Math.sqrt( Math.pow(this.last_position.y - y, 2) + Math.pow(this.last_position.y - y, 2) );
            
            this.last_position = {x: x, y: y};
        } else if(comm[1].charAt(0) == 'Z') {
            if(comm[1].substring(1) == 50.0) {
                this.pen = false;
            } else {
                this.pen = true;
            }
        }

    }
}
