let conn;

function StartGame(btn) {
    btn.innerText = 'RESTART';
    if (window["WebSocket"]) {
        let protocol = 'ws';
        if (document.location.protocol === 'https:') {
            protocol += 's'
        }
        conn = new WebSocket(protocol + '://' + document.location.host + "/first/ws");
        conn.onclose = function (_) {
            btn.innerText = 'START!';
            console.warn('Connection closed.');
        };
        conn.onmessage = function (evt) {
            let data = JSON.parse(evt.data);
            if (data['cmd'] === 'update') {
                on_update(data['field']);
                update_timer(data['timer']);
            } else if (data['cmd'] === 'update_score') {
                document.getElementById('score').innerText =
                    data['score'] + 'P';
            } else if (data['cmd'] === 'settings') {
                for (let i = 2; i < 6; i++) {
                    document.getElementById('conf-value' + i)
                        .innerText = data['settings']['' + i] + 'ds';
                }
            } else if (data['cmd'] === 'game_over') {
                let name = prompt('What is your name?',
                    'anonymous');
                conn.send(JSON.stringify({
                    'cmd': 'name',
                    'name': name,
                }))
            } else if (data['cmd'] === 'history') {
                let ol = document.getElementById('rating');
                Array.from(ol.children).forEach(e => e.remove());
                data['history'].forEach(e => {
                    let li = document.createElement('li');
                    li.innerText = e['name'] + ' [' + e['score'] + ']';
                    ol.insertBefore(li, null);
                });
            } else {
                console.log('unexpected cmd');
                console.log(data);
            }
        };
        conn.onopen = function (_) {
            console.info('WebSocket has opened just');
        };

        conn.onerror = function (error) {
            console.error(error.message);
        };
    } else {
        console.info('Your browser does not support WebSockets.');
    }
};

let choosen = null;

function AskingConf(btn) {
    choosen = btn.id.replace('conf-value', '');
    let root = document.documentElement;
    root.style.setProperty('--display-form', 'block');
    document.getElementById('about-change').innerText = 'for #' + choosen;
}

function SetNewConf() {
    conn.send(JSON.stringify({
        'cmd': 'change_conf',
        'no': choosen,
        'to': parseInt(document.getElementById('how-many').value),
    }));
    document.getElementById('how-many').value = '';
    let root = document.documentElement;
    root.style.setProperty('--display-form', 'none');
}

function update_timer(time_) {
    function _(a) {
        if ((''+a).length === 1) return '0' + a;
        return a.toString()
    }
    document.getElementById('timer').innerText =
        _(Math.floor(time_ / 60)) + ':' + _(time_ % 60)
}

function on_update(field) {
    field.forEach(function (it) {
        let elem = document.getElementById('item' + it['i'] + it['j']);
        if (elem === null) {
            console.error(field);
            return;
        }
        elem.className = "item mark-" + it['color'];
        elem = document.getElementById('inner' + it['i'] + it['j']);
        if (it['of'] === 'xxx') {
            elem.innerText = '';
        } else if (it['of']) {
            elem.innerText = it['tick'] + '/' + it['of'];
        } else {
            elem.innerText = '';
        }
        if (it['color'] === 2) {
            elem.className = 'inner white-text';
        } else {
            elem.className = 'inner';
        }
    })
}

function DoIt(btn, i, j) {
    conn.send(JSON.stringify({
        'cmd': 'do_it',
        'i': i,
        'j': j,
    }))
}
