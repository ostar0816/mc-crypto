navigator.sayswho= (function(){
    var ua= navigator.userAgent, tem,
        M= ua.match(/(opera|chrome|safari|firefox|msie|trident(?=\/))\/?\s*(\d+)/i) || [];
    if(/trident/i.test(M[1])){
        tem=  /\brv[ :]+(\d+)/g.exec(ua) || [];
        return 'IE '+(tem[1] || '');
    }
    if(M[1]=== 'Chrome'){
        tem= ua.match(/\b(OPR|Edge)\/(\d+)/);
        if(tem!= null) return tem.slice(1).join(' ').replace('OPR', 'Opera');
    }
    M= M[2]? [M[1], M[2]]: [navigator.appName, navigator.appVersion, '-?'];
    if((tem= ua.match(/version\/(\d+)/i))!= null) M.splice(1, 1, tem[1]);
    return M.join(' ');
})();

console.log('browser ' + navigator.sayswho);
let wrongBrowser = false;

if(navigator.sayswho.indexOf('IE') !== -1) {
    console.log('here coms');
    $(document).ready(function() {
        $(".note").append("Internet Explorer is not compatible with this site");
        $(".note").css("color", "white");
        $(".notice").css("display", "block");
    });
    wrongBrowser = true;
}

if(navigator.sayswho.indexOf('FF') !== -1) {
    if(parseInt(navigator.sayswho.substr(3)) < 13) {
        $(document).ready(function() {
            $(".note").append("Your browser version is too low. Please update browser.");
            $(".note").css("color", "white");
            $(".notice").css("display", "block");
        });
    }
    wrongBrowser = true;
}

if(navigator.sayswho.indexOf('SF') !== -1) {
    if(parseInt(navigator.sayswho.substr(3)) < 9) {
        $(document).ready(function() {
            $(".note").append("Your browser version is too low. Please update browser.");
            $(".note").css("color", "white");
            $(".notice").css("display", "block");
        });
    }
    wrongBrowser = true;
}

if(navigator.sayswho.indexOf('CH') > -1) {
    if(parseInt(navigator.sayswho.substr(3)) < 38) {
        $(document).ready(function() {
            $(".note").append("Your browser version is too low. Please update browser.");
            $(".note").css("color", "white");
            $(".notice").css("display", "block");
        });
    }
    wrongBrowser = true;
}

if(!wrongBrowser)
    $('.notice').remove();


