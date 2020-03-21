let conn;

function Start(btn) {
    if (window["WebSocket"]) {
        let protocol = 'ws';
        if (document.location.protocol === 'https:') {
            protocol += 's'
        }
        conn = new WebSocket(protocol + '://' + document.location.host + "/ws");
        conn.onclose = function (_) {
            console.warn('Connection closed.');
        };
        conn.onmessage = function (evt) {
            let data = JSON.parse(evt.data);
            console.debug(data);
            if (data['cmd'] === 'update') {
                data['values'].forEach(function (e) {
                    let el = document.getElementById(e['id'] + 'text');
                    el.innerText = e['value'].toFixed(2);
                });
            }
        };
        conn.onopen = function(evt) {
            btn.style.display = 'none';
        };
        conn.onerror = function (error) {
            console.error(error.message);
        };
    } else {
        console.info('Your browser does not support WebSockets.');
    }
}

function act(uuid, s) {
    conn.send(JSON.stringify({
        'cmd': 'act',
        'id': uuid,
        's': s,
    }));
}

$(document).ready(function () {

});
