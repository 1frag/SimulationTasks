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
                    if (['difme', 'stuff'].includes(e['id']))
                        el.innerText = '' + Math.round(e['value']);
                    else
                        el.innerText = e['value'].toFixed(2);

                });
            }
        };
        conn.onopen = function (evt) {
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
let data;
$(document).ready(async function () {
    let resp = await fetch('/meta');
    data = await resp.json();
    setupRightClick(document.body);
    Array.from(document.body.children).forEach(setupRightClick);
    $("#context-menu a").bind("click", function () {
        $(this).parent().removeClass("show").hide();
    });
});

function setupRightClick(el) {
    $(el).bind('contextmenu', function (e) {
        const top = e.pageY;
        const left = e.pageX;
        if(!changeContextMenu(top, left))return false;
        $("#context-menu").css({
            display: "block",
            top: top,
            left: left
        }).addClass("show");
        return false; //blocks default Webbrowser right click menu
    }).bind("click", function () {
        $("#context-menu").removeClass("show").hide();
    });
}

function changeContextMenu(top, left) {
    let result = false;
    const RADIUS = 50;
    data['fields'].forEach(function (e) {
        let el = $('#' + e['id'] + 'text')[0];
        const l = parseInt(el.style.left.replace('px', ''));
        const t = parseInt(el.style.top.replace('px', ''));
        if ( (l - left) * (l - left) + (t - top) * (t - top) <= RADIUS * RADIUS) {
            $('#i1')[0].innerText = e['name'];
            $('#i2')[0].innerText = e['in'];
            result = true;
        }
    });
    return result;
}
