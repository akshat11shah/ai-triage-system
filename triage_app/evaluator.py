import json
import time
import logging
from .models import CustomerMessage, TriageResult, GroundTruth, KBArticle
from .triage_engine import TriageEngine

logger = logging.getLogger(__name__)

# 10 Representative messages from user dataset (includes all categories & types)
RAW_DATASET = [
    {"id": 1, "dataset_category": "Clear", "text": "I made a payment yesterday but it's still showing as pending. Can you check?"},
    {"id": 2, "dataset_category": "Clear", "text": "Please update my phone number to 9876543210."},
    {"id": 3, "dataset_category": "Vague", "text": "It's not working."},
    {"id": 4, "dataset_category": "Angry", "text": "This app is absolutely useless. Nothing ever works!"},
    {"id": 5, "dataset_category": "Multi-Issue", "text": "I can't log in, and even after resetting my password I'm not receiving the OTP."},
    {"id": 6, "dataset_category": "Sarcastic", "text": "Wow, another flawless update. Now literally nothing works. Great job."},
    {"id": 7, "dataset_category": "Out-of-Scope", "text": "What's the weather like in Mumbai today?"},
    {"id": 8, "dataset_category": "Hindi", "text": "मेरा पेमेंट दिखाई नहीं दे रहा है।"},
    {"id": 9, "dataset_category": "Hinglish", "text": "Payment ho gaya hai but dashboard mein show nahi ho raha."},
    {"id": 10, "dataset_category": "Gujarati", "text": "Dashboard ma total amount wrong batave che."}
]

# 10 Hand-labeled Ground Truth cases (representative of edge cases)
GROUND_TRUTH_ITEMS = [
    {
        "text": "I made a payment yesterday but it's still showing as pending. Can you check?",
        "category": "Support Request",
        "priority": "P1",
        "needs_human": False,
        "notes": "Clear message regarding payment pending. Can use KB or customer lookup tool."
    },
    {
        "text": "Please update my phone number to 9876543210.",
        "category": "Account Query",
        "priority": "P2",
        "needs_human": False,
        "notes": "Clear contact change. Easily handled by lookups/guides."
    },
    {
        "text": "It's not working.",
        "category": "Support Request",
        "priority": "P3",
        "needs_human": True,
        "notes": "Extremely vague. Needs human clarification."
    },
    {
        "text": "This app is absolutely useless. Nothing ever works!",
        "category": "Complaint",
        "priority": "P1",
        "needs_human": True,
        "notes": "Angry, abusive, or highly frustrated customer. Priority elevated."
    },
    {
        "text": "I can't log in, and even after resetting my password I'm not receiving the OTP.",
        "category": "Support Request",
        "priority": "P1",
        "needs_human": True,
        "notes": "Multi-issue blocker regarding account security/OTP. High priority."
    },
    {
        "text": "Wow, another flawless update. Now literally nothing works. Great job.",
        "category": "Complaint",
        "priority": "P1",
        "needs_human": True,
        "notes": "Sarcastic complaint about service outage. Needs human triage."
    },
    {
        "text": "What's the weather like in Mumbai today?",
        "category": "Out of Scope",
        "priority": "P3",
        "needs_human": False,
        "notes": "Out of scope request."
    },
    {
        "text": "मेरा पेमेंट दिखाई नहीं दे रहा है।",
        "category": "Support Request",
        "priority": "P1",
        "needs_human": False,
        "notes": "Hindi text meaning 'My payment is not visible'. Should translate and triage as Support Request P1."
    },
    {
        "text": "Payment ho gaya hai but dashboard mein show nahi ho raha.",
        "category": "Support Request",
        "priority": "P1",
        "notes": "Hinglish text meaning payment is done but dashboard doesn't show it. High priority Support Request.",
        "needs_human": False
    },
    {
        "text": "Dashboard ma total amount wrong batave che.",
        "category": "Complaint",
        "priority": "P1",
        "needs_human": True,
        "notes": "Gujarati + English hybrid indicating wrong amount shown on dashboard. Needs human audit."
    }
]

def seed_database():
    """Seeds the 10 raw messages and the 10 ground truth configurations after clearing database."""
    # Clear existing data to maintain exactly 10 items
    TriageResult.objects.all().delete()
    CustomerMessage.objects.all().delete()
    GroundTruth.objects.all().delete()
    KBArticle.objects.all().delete()
    
    # Seed messages
    created_count = 0
    for item in RAW_DATASET:
        msg, created = CustomerMessage.objects.get_or_create(
            text=item["text"],
            defaults={"source": "Dataset"}
        )
        if created:
            created_count += 1
            
    # Seed ground truths
    gt_count = 0
    for item in GROUND_TRUTH_ITEMS:
        gt, created = GroundTruth.objects.get_or_create(
            message_text=item["text"],
            defaults={
                "expected_category": item["category"],
                "expected_priority": item["priority"],
                "expected_needs_human": item.get("needs_human", False),
                "notes": item.get("notes", "")
            }
        )
        if created:
            gt_count += 1

    # Seed dynamic KB articles
    DEFAULT_KB_ARTICLES = [
        {"key": "pending payment", "content": "Policy: Bank transfer payments take up to 24 hours to clear. If a payment is pending >24 hours, ask for transaction details and escalate to Finance."},
        {"key": "phone number update", "content": "Process: To update profile phone numbers, users must navigate to Settings > Profile > Phone. OTP verification on the new number is required."},
        {"key": "download statement", "content": "Guide: Go to Dashboard > Reports > Statement Download, select the month, and click Export."},
        {"key": "password reset", "content": "Guide: Click 'Forgot Password' on the login page. Enter email to receive reset link. Links expire in 15 minutes."},
        {"key": "account locked", "content": "Policy: Accounts lock for 30 minutes after 5 failed login attempts. Contact Support if lock persists."},
        {"key": "delete party", "content": "Policy: A party can only be deleted if it has NO associated payments. If payments exist, the party must be archived instead. Archived parties maintain records."},
        {"key": "otp not received", "content": "Troubleshooting: Check cell signal, check spam folder for email OTP. Delay may be due to carrier congestion. If unresolved, escalate to Tech Support."},
        {"key": "missing payment", "content": "Process: If a payment is missing but completed in bank, check transaction reference and trigger manual sync. Escalate to Billing if not resolved."},
        {"key": "export report", "content": "Guide: Report export requires CSV or PDF selection. If export fails, clear browser cache or try mobile app."}
    ]
    for item in DEFAULT_KB_ARTICLES:
        KBArticle.objects.create(key=item["key"], content=item["content"])
            
    return created_count, gt_count

def evaluate_system():
    """Runs triage evaluation on the 10 ground-truth cases."""
    engine = TriageEngine()
    ground_truths = GroundTruth.objects.all()
    
    if not ground_truths.exists():
        # Seed if empty
        seed_database()
        ground_truths = GroundTruth.objects.all()
        
    results = []
    total_latency = 0.0
    total_tokens = 0
    total_cost = 0.0
    
    correct_category = 0
    correct_priority = 0
    correct_needs_human = 0
    
    failures = []
    
    for gt in ground_truths:
        # Check if we already have a customer message with this text
        msg, _ = CustomerMessage.objects.get_or_create(
            text=gt.message_text,
            defaults={"source": "Evaluation"}
        )
        
        # Check if triage result exists, or run it
        # (For evaluation we run on-demand to measure latency/cost)
        triage_data = engine.triage_message(gt.message_text)
        time.sleep(2.0)  # Rate limit protection for Groq Free Tier (RPS limits)
        
        # Save or update result
        triage_obj, created = TriageResult.objects.get_or_create(message=msg, defaults={
            "category": triage_data["category"],
            "priority": triage_data["priority"],
            "summary": triage_data["summary"],
            "suggested_action": triage_data["suggested_action"],
            "needs_human": triage_data["needs_human"],
            "confidence": triage_data["confidence"],
            "tool_calls_log": json.dumps(triage_data.get("tool_calls", [])),
            "raw_json_response": triage_data.get("raw_json_response", ""),
            "latency": triage_data["latency"],
            "prompt_tokens": triage_data["prompt_tokens"],
            "completion_tokens": triage_data["completion_tokens"],
            "cost": triage_data["cost"]
        })
        
        if not created:
            triage_obj.category = triage_data["category"]
            triage_obj.priority = triage_data["priority"]
            triage_obj.summary = triage_data["summary"]
            triage_obj.suggested_action = triage_data["suggested_action"]
            triage_obj.needs_human = triage_data["needs_human"]
            triage_obj.confidence = triage_data["confidence"]
            triage_obj.tool_calls_log = json.dumps(triage_data.get("tool_calls", []))
            triage_obj.raw_json_response = triage_data.get("raw_json_response", "")
            triage_obj.latency = triage_data["latency"]
            triage_obj.prompt_tokens = triage_data["prompt_tokens"]
            triage_obj.completion_tokens = triage_data["completion_tokens"]
            triage_obj.cost = triage_data["cost"]
            triage_obj.save()
            
        # Link gt back to message
        gt.associated_message = msg
        gt.save()
        
        # Measure agreement
        cat_match = triage_data["category"].lower() == gt.expected_category.lower()
        pri_match = triage_data["priority"] == gt.expected_priority
        human_match = triage_data["needs_human"] == gt.expected_needs_human
        
        if cat_match:
            correct_category += 1
        if pri_match:
            correct_priority += 1
        if human_match:
            correct_needs_human += 1
            
        if not (cat_match and pri_match and human_match):
            failures.append({
                "message": gt.message_text,
                "expected": {
                    "category": gt.expected_category,
                    "priority": gt.expected_priority,
                    "needs_human": gt.expected_needs_human
                },
                "actual": {
                    "category": triage_data["category"],
                    "priority": triage_data["priority"],
                    "needs_human": triage_data["needs_human"]
                },
                "difference": {
                    "category_match": cat_match,
                    "priority_match": pri_match,
                    "needs_human_match": human_match
                }
            })
            
        total_latency += triage_data["latency"]
        total_tokens += (triage_data["prompt_tokens"] + triage_data["completion_tokens"])
        total_cost += triage_data["cost"]
        
        results.append({
            "gt": gt,
            "actual": triage_data
        })
        
    num_cases = len(results)
    
    metrics = {
        "num_cases": num_cases,
        "category_accuracy": (correct_category / num_cases) * 100 if num_cases > 0 else 0,
        "priority_accuracy": (correct_priority / num_cases) * 100 if num_cases > 0 else 0,
        "needs_human_accuracy": (correct_needs_human / num_cases) * 100 if num_cases > 0 else 0,
        "overall_agreement": ((correct_category + correct_priority + correct_needs_human) / (num_cases * 3)) * 100 if num_cases > 0 else 0,
        "total_latency": total_latency,
        "avg_latency": total_latency / num_cases if num_cases > 0 else 0,
        "total_tokens": total_tokens,
        "avg_tokens": total_tokens / num_cases if num_cases > 0 else 0,
        "total_cost": total_cost,
        "avg_cost_per_msg": total_cost / num_cases if num_cases > 0 else 0,
        "failures": failures
    }
    
    return metrics
