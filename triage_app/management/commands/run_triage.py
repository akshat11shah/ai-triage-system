import json
from django.core.management.base import BaseCommand
from tabulate import tabulate
from triage_app.models import CustomerMessage, TriageResult
from triage_app.triage_engine import TriageEngine
from triage_app.evaluator import seed_database, evaluate_system

class Command(BaseCommand):
    help = "Run the AI Customer Message Triage Engine or execute L3 ground-truth evaluation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--message",
            type=str,
            help="Raw customer message to run triage on",
        )
        parser.add_argument(
            "--eval",
            action="store_true",
            help="Run L3 evaluation suite on the 10 ground-truth messages",
        )
        parser.add_argument(
            "--seed",
            action="store_true",
            help="Seed the database with the 40 raw messages and 10 ground-truth entries",
        )
        parser.add_argument(
            "--batch",
            action="store_true",
            help="Triage all unprocessed customer messages in the database",
        ),

    def handle(self, *args, **options):
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')

        if options["seed"]:
            self.stdout.write("Seeding database with dataset...")
            created_msg, created_gt = seed_database()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully seeded: {created_msg} messages, {created_gt} ground-truth entries."
                )
            )
            return

        if options["eval"]:
            self.stdout.write("Running E2E evaluation suite on ground-truth messages...")
            metrics = evaluate_system()
            
            # Print Summary Table
            summary_data = [
                ["Total Test Cases", metrics["num_cases"]],
                ["Category Accuracy", f"{metrics['category_accuracy']:.1f}%"],
                ["Priority Accuracy", f"{metrics['priority_accuracy']:.1f}%"],
                ["Needs Human Accuracy", f"{metrics['needs_human_accuracy']:.1f}%"],
                ["Overall Agreement Rate", f"{metrics['overall_agreement']:.1f}%"],
                ["Avg Latency per Message", f"{metrics['avg_latency']:.2f}s"],
                ["Avg Tokens per Message", f"{metrics['avg_tokens']:.1f} tokens"],
                ["Total Evaluation Cost", f"${metrics['total_cost']:.6f}"],
                ["Avg Cost per Message", f"${metrics['avg_cost_per_msg']:.6f}"],
            ]
            
            self.stdout.write("\n" + "="*50)
            self.stdout.write(" EVALUATION METRICS SUMMARY")
            self.stdout.write("="*50)
            self.stdout.write(tabulate(summary_data, headers=["Metric", "Value"], tablefmt="grid"))
            
            # Print Failures if any
            if metrics["failures"]:
                self.stdout.write("\n" + self.style.WARNING("DISAGREEMENTS / FAILURES:"))
                fail_table = []
                for idx, f in enumerate(metrics["failures"], 1):
                    msg_trunc = f["message"][:40] + "..." if len(f["message"]) > 40 else f["message"]
                    expected_str = f"Cat: {f['expected']['category']}, Pri: {f['expected']['priority']}, Human: {f['expected']['needs_human']}"
                    actual_str = f"Cat: {f['actual']['category']}, Pri: {f['actual']['priority']}, Human: {f['actual']['needs_human']}"
                    fail_table.append([idx, msg_trunc, expected_str, actual_str])
                    
                self.stdout.write(
                    tabulate(
                        fail_table,
                        headers=["#", "Message (Trunc)", "Expected (Ground Truth)", "Actual (AI Engine)"],
                        tablefmt="fancy_grid",
                    )
                )
            else:
                self.stdout.write("\n" + self.style.SUCCESS("Perfect 100% agreement with Ground Truth!"))
            
            self.stdout.write("\nCost Efficiency Note:")
            self.stdout.write("- Estimated cost to process 1,000 messages: " + f"${metrics['avg_cost_per_msg']*1000:.4f}")
            self.stdout.write("- Key cost reduction strategy: Cache repeated queries and use local rule-based filters for trivial Out-of-Scope cases (e.g. weather, jokes) to bypass the LLM completely.")
            return

        if options["batch"]:
            un_triaged = CustomerMessage.objects.filter(triage__isnull=True)
            if not un_triaged.exists():
                self.stdout.write(self.style.SUCCESS("All messages in the database are already triaged."))
                return
            
            self.stdout.write(f"Found {un_triaged.count()} unprocessed messages. Starting batch triage...")
            engine = TriageEngine()
            
            import time
            processed = 0
            total_count = un_triaged.count()
            for idx, msg in enumerate(un_triaged, 1):
                self.stdout.write(f"Processing Msg #{msg.id} ({idx}/{total_count})...")
                triage_data = engine.triage_message(msg.text)
                TriageResult.objects.create(
                    message=msg,
                    category=triage_data["category"],
                    priority=triage_data["priority"],
                    summary=triage_data["summary"],
                    suggested_action=triage_data["suggested_action"],
                    needs_human=triage_data["needs_human"],
                    confidence=triage_data["confidence"],
                    tool_calls_log=json.dumps(triage_data.get("tool_calls", [])),
                    raw_json_response=triage_data.get("raw_json_response", ""),
                    latency=triage_data["latency"],
                    prompt_tokens=triage_data["prompt_tokens"],
                    completion_tokens=triage_data["completion_tokens"],
                    cost=triage_data["cost"]
                )
                processed += 1
                
                # Sleep between requests to avoid 15 RPM rate limits on the free tier
                if idx < total_count and engine.configured:
                    time.sleep(4.5)
                
            self.stdout.write(self.style.SUCCESS(f"Successfully triaged {processed} messages in batch."))
            return

        if options["message"]:
            msg_text = options["message"]
            self.stdout.write(f"Triaging message: '{msg_text}'")
            
            engine = TriageEngine()
            result = engine.triage_message(msg_text)
            
            # Display result table
            res_table = [
                ["Category", result["category"]],
                ["Priority", result["priority"]],
                ["Needs Human Review", "Yes" if result["needs_human"] else "No"],
                ["Confidence Score", f"{result['confidence']:.2f}"],
                ["Summary", result["summary"]],
                ["Suggested Action", result["suggested_action"]],
                ["Latency", f"{result['latency']:.2f}s"],
                ["Estimated Cost", f"${result['cost']:.6f}"],
            ]
            
            self.stdout.write("\n" + "="*50)
            self.stdout.write(" TRIAGE DECISION RESULT")
            self.stdout.write("="*50)
            self.stdout.write(tabulate(res_table, headers=["Attribute", "Value"], tablefmt="fancy_grid"))
            
            # Show tool calls
            if result.get("tool_calls"):
                self.stdout.write("\n" + self.style.SUCCESS("Tools Executed during Triage:"))
                for idx, call in enumerate(result["tool_calls"], 1):
                    self.stdout.write(f"  {idx}. Tool: '{call['tool']}'")
                    self.stdout.write(f"     Args: {call['args']}")
                    self.stdout.write(f"     Result: {call['result']}")
            return

        # Default help prompt if no arguments passed
        self.stdout.write("No arguments provided. Run with --help to see options.")
