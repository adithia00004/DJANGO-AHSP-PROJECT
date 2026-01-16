#!/usr/bin/env python3
"""
Progress Report Generator
Generates visual progress reports from PROGRESS_TRACKER.json
"""

import json
from datetime import datetime
from pathlib import Path


def load_progress_data():
    """Load progress tracking data from JSON file"""
    json_file = Path(__file__).parent / "PROGRESS_TRACKER.json"
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_progress_bar(percentage, width=50):
    """Create ASCII progress bar"""
    filled = int(width * percentage / 100)
    empty = width - filled
    bar = '█' * filled + '░' * empty
    return f"[{bar}] {percentage}%"


def format_status_emoji(status):
    """Get emoji for status"""
    status_map = {
        'completed': '✅',
        'in_progress': '🔄',
        'pending': '⬜',
        'blocked': '🚫',
        'achieved': '✅',
    }
    return status_map.get(status, '❓')


def generate_summary_report(data):
    """Generate executive summary"""
    overall = data['overall']
    project = data['project']

    report = []
    report.append("=" * 80)
    report.append(f"PROJECT PROGRESS REPORT: {project['name']}")
    report.append("=" * 80)
    report.append("")
    report.append(f"📅 Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"📅 Project Start: {project['startDate']}")
    report.append(f"📅 Estimated End: {project['estimatedEndDate']}")
    report.append(f"💰 Budget: ${project['spentBudget']:,.2f} / ${project['totalBudget']:,.2f}")
    report.append(f"⏱️  Hours: {overall['spentHours']} / {overall['totalHours']} hours")
    report.append("")
    report.append("Overall Progress:")
    report.append(create_progress_bar(overall['completion']))
    report.append("")

    return "\n".join(report)


def generate_phase_report(data):
    """Generate phase-by-phase report"""
    report = []
    report.append("=" * 80)
    report.append("PHASE BREAKDOWN")
    report.append("=" * 80)
    report.append("")

    for phase in data['phases']:
        status_emoji = format_status_emoji(phase['status'])
        report.append(f"{status_emoji} Phase {phase['id'].upper()}: {phase['name']}")
        report.append("-" * 80)
        report.append(f"Status: {phase['status'].upper()}")
        report.append(f"Progress: {create_progress_bar(phase['completion'], 40)}")
        report.append(f"Hours: {phase['actualHours']} / {phase['estimatedHours']} hours")

        if phase.get('startDate'):
            report.append(f"Started: {phase['startDate']}")
        if phase.get('endDate'):
            report.append(f"Completed: {phase['endDate']}")

        # Task summary
        tasks = phase.get('tasks', [])
        if tasks:
            completed = sum(1 for t in tasks if t.get('status') == 'completed')
            total = len(tasks)
            report.append(f"Tasks: {completed} / {total} completed")

        # Deliverables
        deliverables = phase.get('deliverables', [])
        if deliverables:
            delivered = sum(1 for d in deliverables if d.get('status') == 'delivered')
            total_deliverables = len(deliverables)
            report.append(f"Deliverables: {delivered} / {total_deliverables} delivered")

        # Metrics
        if phase.get('metrics'):
            report.append("\nKey Metrics:")
            for metric_name, metric_data in phase['metrics'].items():
                if isinstance(metric_data, dict):
                    if 'before' in metric_data and 'after' in metric_data:
                        improvement = metric_data.get('improvement', 0)
                        unit = metric_data.get('unit', '')
                        report.append(f"  • {metric_name}: {metric_data['before']}{unit} → "
                                    f"{metric_data['after']}{unit} ({improvement:+.1f}%)")
                    elif 'target' in metric_data:
                        achieved = metric_data.get('achieved', 'TBD')
                        unit = metric_data.get('unit', '')
                        report.append(f"  • {metric_name}: Target {metric_data['target']}{unit}, "
                                    f"Achieved {achieved}")

        report.append("")

    return "\n".join(report)


def generate_task_report(data):
    """Generate detailed task report"""
    report = []
    report.append("=" * 80)
    report.append("DETAILED TASK LIST")
    report.append("=" * 80)
    report.append("")

    for phase in data['phases']:
        if phase['status'] == 'completed' or phase.get('tasks'):
            report.append(f"\n{phase['name']} - Tasks:")
            report.append("-" * 80)

            for task in phase.get('tasks', []):
                status_emoji = format_status_emoji(task.get('status', 'pending'))
                task_id = task.get('id', '')
                task_name = task.get('name', '')
                hours = task.get('actualHours', 0)
                est_hours = task.get('estimatedHours', 0)

                report.append(f"{status_emoji} [{task_id}] {task_name}")
                report.append(f"     Hours: {hours} / {est_hours}")

                if task.get('subtasks'):
                    for subtask in task['subtasks']:
                        report.append(f"       - {subtask}")

                if task.get('completedDate'):
                    report.append(f"     Completed: {task['completedDate']}")

                report.append("")

    return "\n".join(report)


def generate_milestone_report(data):
    """Generate milestone report"""
    report = []
    report.append("=" * 80)
    report.append("MILESTONES")
    report.append("=" * 80)
    report.append("")

    for milestone in data['milestones']:
        status_emoji = format_status_emoji(milestone['status'])
        report.append(f"{status_emoji} {milestone['name']}")
        report.append(f"   Target: {milestone['targetDate']}")

        if milestone.get('completedDate'):
            report.append(f"   Completed: {milestone['completedDate']} ✅")

        report.append("   Criteria:")
        for criterion in milestone['criteria']:
            report.append(f"      • {criterion}")

        report.append("")

    return "\n".join(report)


def generate_work_session_report(data):
    """Generate work session log"""
    report = []
    report.append("=" * 80)
    report.append("WORK SESSION LOG")
    report.append("=" * 80)
    report.append("")

    for session in data['workSessions']:
        report.append(f"Session #{session['id']} - {session['date']}")
        report.append(f"Duration: {session['duration']} hours")
        report.append(f"Phase: {session['phase']}")
        report.append(f"Tasks: {', '.join(session['tasks'])}")

        if session.get('notes'):
            report.append(f"Notes: {session['notes']}")

        if session.get('blockers'):
            report.append(f"Blockers: {', '.join(session['blockers']) if session['blockers'] else 'None'}")

        report.append("")

    return "\n".join(report)


def generate_documentation_report(data):
    """Generate documentation status"""
    report = []
    report.append("=" * 80)
    report.append("DOCUMENTATION STATUS")
    report.append("=" * 80)
    report.append("")

    total_pages = 0
    completed_docs = 0

    for doc in data['documentation']:
        status_emoji = format_status_emoji(doc['status'])
        pages = doc.get('pages', 0)
        total_pages += pages

        if doc['status'] == 'completed':
            completed_docs += 1

        report.append(f"{status_emoji} {doc['name']}")
        report.append(f"     Pages: {pages}")
        report.append("")

    report.append(f"Total: {completed_docs} / {len(data['documentation'])} documents ({total_pages} pages)")
    report.append("")

    return "\n".join(report)


def generate_full_report(output_file='PROGRESS_REPORT.txt'):
    """Generate complete progress report"""
    data = load_progress_data()

    report_sections = [
        generate_summary_report(data),
        generate_phase_report(data),
        generate_milestone_report(data),
        generate_task_report(data),
        generate_work_session_report(data),
        generate_documentation_report(data),
    ]

    full_report = "\n\n".join(report_sections)

    # Add footer
    full_report += "\n" + "=" * 80 + "\n"
    full_report += f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    full_report += f"Last updated: {data['lastUpdated']}\n"
    full_report += f"Version: {data['version']}\n"
    full_report += "=" * 80 + "\n"

    # Write to file
    output_path = Path(__file__).parent / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_report)

    # Print to console (handle Windows encoding)
    import sys
    if sys.platform == 'win32':
        # Windows console might not support emojis
        print(full_report.encode('ascii', errors='replace').decode('ascii'))
    else:
        print(full_report)

    print(f"\nReport saved to: {output_path}")

    return full_report


if __name__ == '__main__':
    generate_full_report()
