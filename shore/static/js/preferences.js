import * as moment from './moment.min';

$(document).ready(function () {
    const letter = /[a-zA-Z]/;
    const number = /[0-9]/;
    let timeZones = moment.tz.names();
    const $timezoneSelect = $('#preferencesSelectTimezone');
    const apiKeysDiv = $('#apiKeys');

    //console.log('timezones: ', timeZones);
    //console.log('timezones: ', moment.tz(timeZones[0]).format('Z'));

    let options = '';

    timeZones.forEach((item, i) => {
        options += '<option value="' + item +'">' + item + '</option>';
    });

    $timezoneSelect.html(options);

    $('.pref-menu__item').on('click', function() {
        const activeItem = $('.pref-menu__item--active');
        activeItem.removeClass('pref-menu__item--active');
        $(this).addClass('pref-menu__item--active');

        $('html, body').animate({
            scrollTop: $('#' + $(this).data('tosection')).offset().top
        }, 'slow');
    });

    $('#changePassBtn').on('click', function() {
        const currentPass = $('#currentPassword').val();
        const newPass = $('#newPassword').val();
        const newRepeatPass = $('#newRepeatPassword').val();

        if(!currentPass) {
            $('#passWrong').text('Enter your current password please');
            return;
        }

        if (newPass.length < 8 || !letter.test(newPass) || !number.test(newPass)) {
            $('#passWrong').text('Password must be at least 8 characters. With at least one number and one symbol');
            return;
        }

        if(newPass !== newRepeatPass) {
            $('#passWrong').text('Passwords don\'t match');
            return;
        }

        $('#passWrong').text('Your password has been changed');

        setTimeout(() => {
            $('#passWrong').text('');                  
        }, 2000);
    });

    $('#incl-exch').on('change', function() {
        const selectedKeys = $(this).val();
        apiKeysDiv.empty();

        if(selectedKeys && selectedKeys.length > 0) {
            selectedKeys.forEach((item, i) => {
                const twoApiKeys = `
                <div class="col-sm-3">
                    <h6 class="pref__control--panel">${item} keys:</h6>
                </div>
                <div class="pref__form-group no-gutter">
                    <div class="col-sm-12">
                        <input type="text" id="key1-${item}" class="main__input" placeholder="${item} key1"/>
                        <input type="text" id="key2-${item}" class="main__input" placeholder="${item} key2"/>
                    </div>
                </div>`;

                apiKeysDiv.append(twoApiKeys);
            });
        }
    });

});
$('.preferences-menu').css('height', $('.pref-content__main').innerHeight());
