/*const secret = window.otplib.authenticator.generateSecret();
const token = window.otplib.authenticator.generate(secret);
*/

$(document).ready(function () {
    $('#id_sms-number').intlTelInput({
        autoHideDialCode: false,
        separateDialCode: true
    });

    $('.iti-flag').css('left', '5px');
    $('.selected-dial-code').text('(' + $('.selected-dial-code').text() + ')');

    $('.country-list').on('click', 'li' ,function() {
        setTimeout(() => {
            $('.selected-dial-code').text('(' + $('.selected-dial-code').text() + ')');
        });
    });
});

const googleAuthTpl = `
            <h3 class="two_fa_auth_h3">Google Authenticator</h3>
            
            <p class="two_fa_auth_h3">
                1. Download Google Authenticator on <i>AppStore</i><br>
                or <i>GooglePlay</i>
                <br>
                2. Scan QR-Code via Google Authenticator:
            </p>
            <div id="qrcode"></div>
            
            <p class="two_fa_auth_h3" style="margin-top: 15px">
                3. Enter 6-digits verification code:
                
                <input class="form-input" type="number" id="googleAuthNumber" placeholder="Name">
            </p>
        `;

const smsAuthTpl = `
            <p class="two_fa_auth_h3" style="margin-top: 15px">
                Enter your phone number:
                
                <input class="form-input" type="tel" id="phoneAuthNumber" placeholder="Your phone">
            </p>
        `;

//document.getElementById('two_fa_auth_content').innerHTML = googleAuthTpl;

/*let qrcode = new QRCode("qrcode", {
    text: secret,
    width: 128,
    height: 128,
    colorDark : "#000000",
    colorLight : "#ffffff",
    correctLevel : QRCode.CorrectLevel.H
});*/

function radioAuthClicked() {
    const googleAuth = document.getElementById('googleAuthRadio').checked;

    if(googleAuth) {
        document.getElementById('smsAuthDiv').style.display = 'none';
        document.getElementById('googleAuthDiv').style.display = 'block';
        document.getElementById('two_fa_auth_content').innerHTML = googleAuthTpl;

        qrcode = new QRCode("qrcode", {
            text: secret,
            width: 128,
            height: 128,
            colorDark : "#000000",
            colorLight : "#ffffff",
            correctLevel : QRCode.CorrectLevel.H
        });
    } else {
        document.getElementById('googleAuthDiv').style.display = 'none';
        document.getElementById('smsAuthDiv').style.display = 'block';
    }
}

/*document.querySelector("#two_fa_auth_form").addEventListener("submit", function(e){
    e.preventDefault();

    const authNumber = document.getElementById('googleAuthNumber').value;
    console.log(authNumber);

    if(authNumber) {
        if(token === authNumber) {
            //alert('ok');
            window.location.href = '/two-factor-api-keys';
        } else {
            alert('Wrong verification code');
        }
    } else {
        alert('Please insert verification code to continue');
    }
});

document.querySelector("#submitTwoFaSMSAuthForm").addEventListener("click", function(e){
    e.preventDefault();

    const phoneNumber = document.getElementById('phoneAuthNumber').value;

    if(phoneNumber) {
        alert('SMS sent');
    } else {
        alert('Please insert phone number');
    }

});
*/