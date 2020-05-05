let conn, series, name = null;
let PreviousData = null;
let maxX, maxY;


$(document).ready(function () {
    if (window["WebSocket"]) {
        let protocol = 'ws';
        if (document.location.protocol === 'https:') {
            protocol += 's'
        }
        conn = new WebSocket(protocol + '://' + document.location.host + "/fourth/ws");
        conn.onclose = function (_) {
            console.warn('Connection closed.');
        };
        conn.onmessage = function (evt) {
            let data = JSON.parse(evt.data);
            //console.debug(data);
            if (data['cmd'] === 'pd') {
                PreviousData = data['data'];
                drawChart();
            } else if (data['cmd'] === 'upd') {
                series.addPoint([data['x'], data['y']], true, true);
                $('#price')[0].innerText = 'Price: ' + data['y'].toFixed(2);
                updateTop(data['top']);
            } else if (data['cmd'] === 'not_enough_money') {
                alert('Вам не хватает денег чтобы купить акцию');
            } else if (data['cmd'] === 'not_enough_count') {
                alert('Вы не можете продать не имея ни одной акции');
            } else if (data['cmd'] === 'balance') {
                $('#money')[0].innerText = 'Money: ' + data['money'].toFixed(2);
                $('#count')[0].innerText = 'Count: ' + data['count'];
            } else if (data['cmd'] === 'error') {
                alert(data['e']);
            }
        };
        conn.onopen = function (_) {
            name = prompt('Input your login');
            conn.send(JSON.stringify({
                'cmd': 'hi',
                'login': name,
            }))
        };

        conn.onerror = function (error) {
            console.error(error);
        };
    } else {
        console.info('Your browser does not support WebSockets.');
    }
});

function sendCmd(cmd) {
    conn.send(JSON.stringify({
        'cmd': cmd,
    }))
}

function updateTop(rate) {
    let ol = $('#rating')[0];
    Array.from(ol.children).forEach(e => e.remove());
    rate.reverse();
    rate.forEach(e => {
        let li = document.createElement('li');
        li.className = 'txt';
        if (e['name'] === name && name !== null) {
            li.className += ' is_you';
        }
        li.innerText = e['name'] + '[' + e['money'].toFixed(2) + ']';
        ol.insertBefore(li, null);
        let br = document.createElement('br');
        ol.insertBefore(br, null);
    });
}
