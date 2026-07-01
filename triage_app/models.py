from django.db import models

class CustomerMessage(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=50, default='Web')

    def __str__(self):
        return f"Message {self.id}: {self.text[:50]}..."

class TriageResult(models.Model):
    PRIORITY_CHOICES = [
        ('P0', 'P0 (Critical)'),
        ('P1', 'P1 (High)'),
        ('P2', 'P2 (Medium)'),
        ('P3', 'P3 (Low)'),
    ]

    message = models.OneToOneField(CustomerMessage, on_delete=models.CASCADE, related_name='triage')
    category = models.CharField(max_length=100)
    priority = models.CharField(max_length=2, choices=PRIORITY_CHOICES)
    summary = models.TextField()
    suggested_action = models.TextField()
    needs_human = models.BooleanField(default=False)
    confidence = models.FloatField()
    
    # Execution Metadata
    tool_calls_log = models.TextField(blank=True, null=True, help_text="JSON representation of tool calls and results")
    raw_json_response = models.TextField(blank=True, null=True)
    latency = models.FloatField(default=0.0, help_text="Latency in seconds")
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    cost = models.FloatField(default=0.0)
    
    # AI Generation
    auto_reply_draft = models.TextField(blank=True, null=True)
    
    # Human Override fields
    is_overridden = models.BooleanField(default=False)
    overridden_category = models.CharField(max_length=100, blank=True, null=True)
    overridden_priority = models.CharField(max_length=2, choices=PRIORITY_CHOICES, blank=True, null=True)
    overridden_needs_human = models.BooleanField(blank=True, null=True)
    overridden_summary = models.TextField(blank=True, null=True)
    overridden_suggested_action = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Triage for Msg {self.message.id} [{self.category} / {self.priority}]"

    @property
    def final_category(self):
        return self.overridden_category if self.is_overridden else self.category

    @property
    def final_priority(self):
        return self.overridden_priority if self.is_overridden else self.priority

    @property
    def final_needs_human(self):
        return self.overridden_needs_human if self.is_overridden else self.needs_human

    @property
    def final_summary(self):
        return self.overridden_summary if self.is_overridden and self.overridden_summary else self.summary

    @property
    def final_suggested_action(self):
        return self.overridden_suggested_action if self.is_overridden and self.overridden_suggested_action else self.suggested_action

class GroundTruth(models.Model):
    message_text = models.TextField()
    expected_category = models.CharField(max_length=100)
    expected_priority = models.CharField(max_length=2, choices=TriageResult.PRIORITY_CHOICES)
    expected_needs_human = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    # Link to a triaged instance if evaluated
    associated_message = models.ForeignKey(CustomerMessage, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"GroundTruth: {self.message_text[:50]}..."

class KBArticle(models.Model):
    key = models.CharField(max_length=100, unique=True, help_text="Search match keyword (e.g. pending payment)")
    content = models.TextField(help_text="Article contents and guidelines")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key

# =====================================================================
# Background ML Auto-Training Trigger
# =====================================================================
import threading
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)
ml_training_lock = threading.Lock()

def run_ml_training_thread():
    if not ml_training_lock.acquire(blocking=False):
        # Model is already currently training, skip this duplicate request
        return
    try:
        from .ml_classifier import train_fallback_model
        train_fallback_model()
    except Exception as e:
        logger.error(f"Background ML training failed: {e}")
    finally:
        ml_training_lock.release()

@receiver(post_save, sender=TriageResult)
def auto_train_ml_fallback(sender, instance, created, **kwargs):
    if created:
        # Spin up a background daemon thread so the web UI isn't blocked!
        thread = threading.Thread(target=run_ml_training_thread)
        thread.daemon = True
        thread.start()
