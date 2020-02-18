let conn, cnvs, ctx, ticker;
let HEIGHT = 525, WIDTH = 825, STEP = 75;
let INDENT = 10;
let maxX, maxY;

function StartExp(btn) {
    btn.disabled = true;
    let curX, curY, h0;

    function _x(x) {
        return x / maxX * WIDTH;
    }

    function _y(y) {
        return HEIGHT - (y / maxY * HEIGHT);
    }

    if (window["WebSocket"]) {
        let protocol = 'ws';
        if (document.location.protocol === 'https:') {
            protocol += 's'
        }
        conn = new WebSocket(protocol + '://' + document.location.host + "/ws");
        conn.onclose = function (_) {
            btn.disabled = false;
            console.warn('Connection closed.');
        };
        conn.onmessage = function (evt) {
            let data = JSON.parse(evt.data);
            console.debug(data);
            if (data['cmd'] === 'resize') {
                maxX = data['maxX'];
                maxY = data['maxY'];
                SetMaximums();
                curX = 0;
                curY = _y(h0);
            } else if (data['cmd'] === 'update') {
                ctx.beginPath();
                ctx.moveTo(curX + INDENT, curY);
                curX = _x(data['x']);
                curY = _y(data['y']);
                ctx.lineTo(curX + INDENT, curY);
                ctx.closePath();
                ctx.lineWidth = 3;
                ctx.strokeStyle = '#06ad06';
                ctx.stroke();
                ticker.innerText = data['time'].toFixed(1);
            } else if (data['cmd'] === 'error') {
                alert('Данные введены неправильно или содержат ошибку')
            }
        };
        conn.onopen = function (__) {
            ctx.clearRect(0, 0, WIDTH + INDENT, HEIGHT);
            let manager = document.getElementById('manager');
            manager.value = 'Stop';
            stopped = false;
            try {
                console.info('WebSocket has opened just');
                h0 = parseFloat(document.getElementById('height').value);
                conn.send(JSON.stringify({
                    'cmd': 'init',
                    'h0': h0,
                    'a': parseFloat(document.getElementById('angle').value),
                    'v0': parseFloat(document.getElementById('speed').value),
                }));
            } catch (e) {
                console.error(e);
                conn.close();
            }
        };

        conn.onerror = function (error) {
            console.error(error.message);
        };
    } else {
        console.info('Your browser does not support WebSockets.');
    }
}

let stopped = false;

function StopExp(btn) {
    if (stopped) {
        conn.send(JSON.stringify({'cmd': 'continue'}));
        btn.value = 'Stop';
    } else {
        conn.send(JSON.stringify({'cmd': 'stop'}));
        btn.value = 'Continue';
    }
    stopped = 1 - stopped;
}

$(document).ready(function () {
    cnvs = document.getElementById("cnvs");
    ctx = cnvs.getContext('2d');
    ticker = document.getElementById('ticker');
});

function SetMaximums() {
    ctx.font = '10px Arial';
    ctx.fillText("0", 0, HEIGHT);
    ctx.beginPath();
    for (let i = STEP; i < WIDTH; i += STEP) {
        ctx.fillText((i / WIDTH * maxX).toFixed(2) + '', i - 3, HEIGHT);
        ctx.moveTo(i + INDENT, HEIGHT);
        ctx.lineTo(i + INDENT, 0);
    }
    for (let i = STEP; i < HEIGHT; i += STEP) {
        ctx.fillText((i / HEIGHT * maxY).toFixed(2) + '', 0, HEIGHT - i);
        ctx.moveTo(0, HEIGHT - i);
        ctx.lineTo(WIDTH + INDENT, HEIGHT - i);
    }
    ctx.closePath();
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 0.5;
    ctx.stroke();
}
