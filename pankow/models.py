import uuid

from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import JSONField
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from pankow.const import TaskState, ExecutionType, LoopTag

TP_STATUS = (
    (TaskState.STATE_NONE.value, _('Trade not started')),
    (TaskState.STATE_PROGRESS.value, _('Trade in progress')),
    (TaskState.STATE_STEP_PASSED.value, _('Trade step passed')),
    (TaskState.STATE_SUCCESS.value, _('Trade success for single exchange')),
    (TaskState.STATE_COMPLETED.value, _('Trade completed')),
    (TaskState.STATE_FAILED.value, _('Trade failed')),
)

TP_EXEC_TYPE = (
    (ExecutionType.SEQUENTIAL.value, _('Sequential')),
    (ExecutionType.PARALLEL.value, _('Parallel')),
)

TP_LOOP_TAG = (
    (LoopTag.VERIFY_PAYLOAD.value, _('Verify payload')),
    (LoopTag.BALANCE.value, _('Check balance')),
    (LoopTag.PLACE_ORDER.value, _('Place order')),
    (LoopTag.ORDER_STATUS.value, _('Order status')),
    (LoopTag.FINAL_STATUS.value, _('Final status')),
    (LoopTag.CONNECTION_ERROR.value, _('Connection error')),
)


LENGTH = 50
MAX_TRIES = 32


class TradePlan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tradeplan')
    auth_token = models.CharField(
        max_length=LENGTH,
        editable=False,
        unique=True)
    loop = ArrayField(
        ArrayField(
            models.CharField(
                max_length=255),
            blank=True,
            default=[]))
    amount = ArrayField(
        ArrayField(
            models.CharField(
                max_length=255),
            blank=True,
            default=[]))
    exec_type = models.CharField(
        max_length=255,
        default=ExecutionType.SEQUENTIAL.value,
        choices=TP_EXEC_TYPE,
        verbose_name=_('exec_type'),
        blank=True)
    check_balance = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(default=timezone.now, blank=True)
    status = models.CharField(
        max_length=255,
        default=TaskState.STATE_NONE.value,
        choices=TP_STATUS,
        verbose_name=_('status'),
        blank=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            loop_num = 0
            unique = False
            while not unique:
                if loop_num < MAX_TRIES:
                    new_code = uuid.uuid4()
                    if not TradePlan.objects.filter(auth_token=new_code):
                        self.auth_token = new_code
                        unique = True
                    loop_num += 1
                else:
                    raise ValueError("Couldn't generate a unique token.")
        super(TradePlan, self).save(*args, **kwargs)


class ActionLog(models.Model):
    trade_plan = models.ForeignKey(
        TradePlan,
        on_delete=models.CASCADE,
        related_name='actionlog')
    # Start time to group action logs with the same trade plan
    start_time = models.DateTimeField(default=timezone.now, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, blank=True)
    exchange = models.CharField(max_length=255, default='', blank=True)
    loop_num = models.IntegerField(default=0, blank=True)
    loop_tag = models.CharField(
        max_length=255,
        default=LoopTag.VERIFY_PAYLOAD.value,
        choices=TP_LOOP_TAG,
        blank=True
    )
    additional_info = JSONField()
