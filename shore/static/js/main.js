import * as moment from './moment.min';

import {addColorToDelta, format, formatSteps, formatChart, preferenceFormSave}
       from './utils';

import './bootstrapModal.min.js';
import './bootstrapAccordion.min.js';
import './checkBrowser';
import './preferences';
import './jsrender.min.js';

const port = 9999;
console.log('hostname:', window.location.hostname);

let ws_protocol;
if (window.location.protocol === "https:") {
    ws_protocol = 'wss://';
} else {
    ws_protocol = 'ws://';
}

window.socket = new WebSocket(ws_protocol + window.location.hostname + ':' + port);
window.socket.binaryType = "arraybuffer";

$(function () {
    let urlParamsMap = new Map();
    window.detailsOpened = 0;
    window.allSelected = true;
    window.allSelectedChanged = false;

    socket.onopen = function() {
        console.log("Connected!");
        window.socketIsOpened = true;
    }

    socket.onmessage = function(e) {
        console.log("Response received: " + e.data);

        let loop = JSON.parse(e.data);
        if(loop.status == 'completed' || loop.status == 'failed') {
            window.tradingOn = false;
        }
        $('.steps').html('<div class="row" align="center">' + loop.loop_tag  + '</div>');
    }

    socket.onclose = function(e) {
        console.log("Connection closed.");
        socket = null;
        window.socketIsOpened = false;
    }

    preferenceFormSave();

    const tgts = ['incl-curr'];

    const placeholders = [
        ' i.e. BTC or ETH or XRP...',
    ];
    const inclExchsBtnsBlock = $('.includeExchangesButtons');

    const selects = new Map();

    let selectedExchanges = [];
    const $inclSelect = $('#incl-exch');
    const $inclCurrSelect = $('#incl-curr');

    setTimeout(() => {
        let urlParamsKeyValues = new Map();

        if(typeof regions !== 'undefined') {
            Object.keys(regions).forEach(key => {
                inclExchsBtnsBlock.append('<button class="btn btn--default btn--box btn--white" data-group="' + key + '">' + key.toUpperCase() + '</button>');
            });
        }

        $('.includeExchangesButtons button').on('click', function() {
            const btnGroup = $(this).data('group');

            if($(this).attr('id') === 'allIncludeExchgs'
                || $(this).attr('id') === 'noneIncludeExchgs'
                || $(this).attr('id') === 'updateTableBtn') {
                return;
            }

            if(window.allSelected)
                $('.includeExchgsCheck').prop('checked', false);

            if(allSelected && allSelectedChanged) {
                $('.includeExchgsCheck').each((i, checkbox) => {
                    if(regions[btnGroup + ''].indexOf($(checkbox).data('inputgroup')) <= 0) {
                        $(checkbox).trigger('click');
                    }
                });
            } else {
                $('.includeExchgsCheck').each((i, checkbox) => {
                    if((regions[btnGroup + ''].indexOf($(checkbox).data('inputgroup')) > 0)) {
                        $(checkbox).trigger('click');
                    }
               });
            }

            $(this).toggleClass('btn--white includeExchangesActiveButton');
            window.allSelected = false;
            window.allSelectedChanged = true;
        });
    }, 0);

    for (var i = 0; i < tgts.length; i++) {
        const name = tgts[i];
        const sel = $('#' + name).select2({
            width: 'resolve',
            placeholder: placeholders[i],
            theme: 'spectre',
            escapeMarkup: (m) => m,
        });
        selects.set(name, sel);

        let urlParamsKeyValues = new Map();

        let urlParams = decodeURIComponent(location.hash).substr(1).split('&').forEach(item => {
            const keyValArr = item.split('=');
            let valArr;

            if(keyValArr[1] && keyValArr[1] !== '')
                valArr = keyValArr[1].split(',');
            else
                valArr = [];

            if(valArr.length > 0) {
                valArr.forEach(item => {
                    $('.includeExchgsCheck.' + item).trigger('click');
                    $inclSelect.val(item).trigger('change');
                 });
             }

            urlParamsKeyValues.set(keyValArr[0].trim(), valArr);
            urlParamsMap.set(keyValArr[0].trim(), valArr.join(','));
        });

        const saved3 = urlParamsKeyValues.get(name) || [];

        sel.val(saved3);
        sel.trigger('change');
        // prevent the dropdown from opening when unselecting,
        // which is unneeded and annoying
        sel.on('select2:unselecting', function(ev) {
            if (ev.params.args.originalEvent) {
                // When unselecting (in multiple mode)
                ev.params.args.originalEvent.stopPropagation();
            } else {
                // When clearing (in single mode)
                $(this).one('select2:opening', ev => ev.preventDefault());
            }
        });
    }

    const includeArrowL = $('<span class="arrow_carrot-left_alt2 select2-before"></span>');
    const includeArrowR = $('<span class="arrow_carrot-right_alt2 select2-after"></span>');

    const inclCurrSelectWidth = parseInt($('span .select2-selection').css('width'));

    const includeUl = $('.select2-selection__rendered');
    let marginLeft = parseInt(includeUl.css('margin-left'));

    const leftArrowClicked = function () {
        marginLeft += 16;
        includeUl.css('margin-left', marginLeft);
    };

    const rightArrowClicked = function () {
        marginLeft -= 16;
        includeUl.css('margin-left', marginLeft);
    };

    $inclCurrSelect.on('change', function () {
        $('.arrow_carrot-left_alt2, .arrow_carrot-right_alt2').remove();

        let wid = 0;
        $(includeUl).children('.select2-selection__choice').each((i, li) => {
            wid += parseInt($(li).css('width'));
        });

        if(wid >= inclCurrSelectWidth - 20) {
            $('.select2').prepend(includeArrowL);
            $('.select2').append(includeArrowR);

            let int1, int2;

            $(includeArrowL).mousedown(function() {
                int1 = setInterval(leftArrowClicked, 100);
            }).mouseup(function() {
                clearInterval(int1);
            });

            $(includeArrowR).mousedown(function() {
                int2 = setInterval(rightArrowClicked, 100);
            }).mouseup(function() {
                clearInterval(int2);
            });

            $(includeArrowL).on('mousedown', function () {
                leftArrowClicked();
            });

            $(includeArrowR).on('mousedown', function () {
                rightArrowClicked();
            });
        } else {
            marginLeft = 0;
            includeUl.css('margin-left', marginLeft);

            let ul = $('.select2-selection').find('.select2-selection__rendered');
            $('.select2-selection__rendered').remove();

            setTimeout(() => {
                $('.select2-selection').prepend(ul);
            }, 0);
        }
    });

    $inclSelect.children('option').each((i, elem) => {
        selectedExchanges.push($(elem).val());
    });

    let checkedBoxes = [];

    $('.includeExchgsCheck').on('change', function() {
        $inclSelect.val(null).trigger('change');
        const paragraphText = $(this).next('p').text();

        if(this.checked) {
            selectedExchanges.push(paragraphText);
            checkedBoxes.remove(paragraphText);
        } else {
            selectedExchanges.remove(paragraphText);
            checkedBoxes.push(paragraphText);
        }
        $inclSelect.val(checkedBoxes).trigger('change');

        if(checkedBoxes.length) {
            window.allSelected = false;
            window.allSelectedChanged = true;
        } else {
            window.allSelected = true;
            window.allSelectedChanged = true;
        }
    });

    //$.fn.dataTable.ext.classes.sPaging = 'dataTables_paginate pagination paging_';
    //$.fn.dataTable.ext.classes.sPageButton = 'paginate_buttom page_item';

    const registrationNotAcceptedModal = `
        <div class="modal fade" id="registration-not-accepted-modal" role="dialog" data-keyboard="false" data-backdrop="static">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <div class="row">
                            <div class="col-xs-6"><h4 class="modal-title" style="display: inline-block">Sorry!</h4></div>
                            <div class="col-xs-4 col-xs-offset-2"><a href="javascript:void(0)" class="close closeStartTradesModal" aria-label="Close" data-dismiss="modal" style="display: inline-block">X</a></div>
                        </div>
                    </div>
                    <div class="modal-body" style="background-color: #D5DBDB">
                        <h6 style="font-size: 14px">Right now registrations are still closed. To get early access, sign up at <a id="goToMacChain" href="http://macchina.com/">macchina.com</a></h6>
                    </div>
                </div>

            </div>
        </div>
    `;

    if($('#registration-not-accepted-modal').length <= 0) {
        $('body').append(registrationNotAcceptedModal);
    }

    var dt = $('#dt_table').DataTable({
        serverSide: true,
        processing: true,
        searching: false,
        responsive: true,
        lengthChange: true,
        buttons: true,
        bLengthChange: false,
        ajax: {
            url: typeof dtUrl !== 'undefined' ? dtUrl : '',
            dataSrc: 'data',
            type: 'GET',
            data: function(args) {
                for (var i = 0; i < tgts.length; i++) {
                    const name = tgts[i];

                    args[name] = $('#' + name).select2('data').map(o => o.text);
                }
                args['incl-exch'] = $('.includeExchgsCheck:checkbox:checked').map(
                        function() {
                            return this.id;
                        }
                    ).get();
                args['minvol'] = $('#volumeInput').val();
                args['only-simul'] = $('#onlySimulExchs').prop('checked');

                return {
                    'args': JSON.stringify(args)
                };
            }
        },
        columns: [
            { data: 'best_taker_pl',
              responsivePriority: 1,
              render: function(data, type, row) {
                  if (type === 'display' || type === 'filter') {
                      let par = parseFloat(data.parallel) * 100;
                      let seq = parseFloat(data.sequential) * 100;
                      return Math.min(par, seq).toFixed(2) + '%';
                  } else {
                      return data;
                  }
                },
            },
            { data: 'spread',
              responsivePriority: 2,
              render: function(data, type, row) {
                  return (type === 'display' || type === 'filter') ?
                      (parseFloat(data) * 100).toFixed(2) + '%' :
                      parseFloat(data);
                },
            },
            { data: 'dt',
              responsivePriority: 3,
              render: function(data, type, row) {
                  const m = moment.parseZone(data).local();
                  if (type === 'filter') return m;
                  return type === 'display' ?
                      addColorToDelta(m.fromNow()) :
                      data;
                },
            },
            { data: 'minvol',
                responsivePriority: 4,
                render: function(data, type, row) {
                    return (Math.round(parseFloat(data) * 100) / 100).toFixed(2);
                },
            },
            {
                data: 'exchanges',
                responsivePriority: 5,
                render: function (data, type, row) {
                    return (type === 'display' || type === 'filter') ?
                        Object.values(data).join(', ') :
                        data;
                },
            },
            { data: 'currencies',
              responsivePriority: 5,
              render: '[, ]',
            },
            { data: 'empty',
                responsivePriority: 7,
                render: function(data, type, row) {
                    const checked = data ? 'icon_close' : 'icon_check';
                    return `<span aria-hidden="true" class="${checked} table-td__icon"></span>`;
                },
            },
            { data: 'amounts' },
            { data: 'trades' },
            { data: 'spread_info' },
            { data: 'amounts_ticker' },
            { data: 'signed_spread' },
            { data: 'one_fee' },
            { data: 'best_taker_amount' },
        ],
        columnDefs: [
            //{ targets: [0, 1, 3], className: 'text-right' },
            { targets: [-7, -6, -5, -4, -3, -2, -1], visible: false },
            { targets: -8, className: 'last-td'}
        ],
        pageLength: 25,
        order: [
            [0, 'desc'],
        ],
    });


    const detailRows = [];
    let timePassed = 0;
    let timePassedInterval;
    let cancelReload = false;

    const dtReloadInterval = setInterval(function() {
        if(detailsOpened === 0 && !cancelReload)
            dt.ajax.reload();

        if(timePassedInterval) {
            cancelReload = false;
            return;
        }

        timePassedInterval = setInterval(function() {
            timePassed++;
            if(timePassed >= 50 && !cancelReload) {
                $('#reloadTimeRemains').css('display', 'block');
                $('#reloadTimeRemains span').text(60 - timePassed);
            }
            if(timePassed === 60) {
                $('#reloadTimeRemains').css('display', 'none');
                timePassed = 0;
            }
        }, 1000);
    }, 60000);

    $('#preventReloadBtn').on('click', function () {
        cancelReload = true;

        const $canceledReload = $('<h5 id="canceledReload">Canceled reload</h5>');
        const $reloadTimeRemains = $('#reloadTimeRemains');

        $reloadTimeRemains.css('display', 'none');
        $reloadTimeRemains.after($canceledReload);

        $canceledReload.fadeOut('slow');
    });

    $('#dt_table tbody').on('click', 'tr td',function () {
        var tr = $(this).closest('tr');
        // Ignore click event for child
        if (!tr.attr("class")) {
            return;
        }

        var row = dt.row(tr);
        var idx = $.inArray(tr.attr('id'), detailRows);
        if (idx != -1) {
            tr.removeClass('details');
            row.child.hide();
            detailsOpened--;
            // Remove from the 'open' array
            detailRows.splice(idx, 1);
        } else {
            // XXX: save the detail in local storage
            tr.addClass('details');
            row.child(format(row.data())).show();
            detailsOpened++;
            // Add to the 'open' array
            if (idx === -1) {
                detailRows.push(tr.attr('id'));
            }
        }
    });

    const preferenceSelect = $('.prefExclSelect');

    preferenceSelect.on('change', () => {
        $('.prefExclInputDiv').remove();

        const selectValues = preferenceSelect.val();

        if(selectValues && selectValues.length) {
            const saveBtnDiv = $('#preferencesSubmit');
            const keysDiv = $('<div id="exclApiKeys" class="columns"></div>');
            saveBtnDiv.before(keysDiv);

            selectValues.forEach((item, i) => {
                const id1 = item + '-1',
                      id2 = item + '-2';

                const input1 = $('<div class="pref__form-group no-gutter"><div class="col-sm-3"><label class="pref__control--panel" for="' + id1 + '"> key 1:</label></div><div class="col-sm-9 exclApiInputs"><input type="text" class="main__input" id="' + id1 + '"></div></div>');
                const input2 = $('<div class="pref__form-group no-gutter"><div class="col-sm-3"><label class="pref__control--panel" for="' + id2 + '"> key 2:</label></div><div class="col-sm-9 exclApiInputs"><input type="text" class="main__input" id="' + id2 + '"></div></div>');

                const div = $('<div class="col-12 col-mx-auto prefExclInputDiv"></div>');
                div.append(input1).append(input2);

                keysDiv.append(div);
            });
        }
    });

    for (var i = 0; i < tgts.length; i++) {
        const name = tgts[i];
        const sel = $('#' + name);

        if(name === 'incl-exch')
            continue;
    }

    //Check to see if the window is top if not then display button
	$(window).scroll(function(){
		if ($(this).scrollTop() > 200) {
			$('.scrollToTop').fadeIn();
		} else {
			$('.scrollToTop').fadeOut();
		}
	});

	//Click event to scroll to top
	$('.scrollToTop').click(function(){
		$('html, body').animate({scrollTop : 0},800);
		return false;
	});

	$('#incl-exch').hide();
    $('.select2.select2-container').eq(1).hide();

    $('#noneIncludeExchgs').on('click', function () {
        window.allSelected = false;
        window.allSelectedChanged = true;
        $('.includeExchangesButtons button:not(#allIncludeExchgs, #noneIncludeExchgs)').removeClass('includeExchangesActiveButton').addClass('btn--white');

        //$('.includeExchgsCheck').prop('checked', false);
        $('.includeExchangesContent .includeExchgsCheck').each((i, checkbox) => {
            if(checkbox.checked) {
                $(checkbox).trigger('click');
            }
        });
    });

    $('#allIncludeExchgs').on('click', function () {
        window.allSelected = true;
        window.allSelectedChanged = true;
        $('.includeExchangesButtons button:not(#allIncludeExchgs, #noneIncludeExchgs)')
            .removeClass('btn--white').addClass('includeExchangesActiveButton');

        $('.includeExchangesContent .includeExchgsCheck').each((i, checkbox) => {
            if(!checkbox.checked) {
                $(checkbox).trigger('click');
            }
        });
    });

    $('#updateTableBtn').on('click', function() {
        dt.ajax.reload();
    });
});

$('.user-name').click(function(e){
    $('.dropdown').toggleClass('collapse-in');
    e.stopPropagation();
});

$('#createAccount').on('click', function () {
    $('#registration-not-accepted-modal').modal('show');
});

$(document).click(function(){
    // Close the callout by clicking out
    var dropdown = $('.dropdown');
    if (dropdown && dropdown.hasClass('collapse-in')) {
        dropdown.removeClass('collapse-in');
    }
});
