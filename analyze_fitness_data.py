#!/usr/bin/env python3
"""
Fitness Data Analyzer
Reads CSV exports from fitness_tracker.html and generates HTML reports.

Usage:
    python analyze_fitness_data.py                    # Analyze all CSVs in current folder
    python analyze_fitness_data.py /path/to/csvs     # Analyze CSVs in specific folder
    python analyze_fitness_data.py --watch           # Watch folder for new CSVs
"""

import os
import sys
import glob
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
CSV_FOLDER = Path(__file__).parent / "csv_imports"
REPORT_FOLDER = Path(__file__).parent / "reports"


def ensure_folders():
    """Create necessary folders if they don't exist."""
    CSV_FOLDER.mkdir(exist_ok=True)
    REPORT_FOLDER.mkdir(exist_ok=True)
    print(f"📁 CSV folder: {CSV_FOLDER}")
    print(f"📁 Reports folder: {REPORT_FOLDER}")


def load_workouts():
    """Load all workout CSVs."""
    files = glob.glob(str(CSV_FOLDER / "workouts_*.csv"))
    if not files:
        return pd.DataFrame()

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"⚠️  Error reading {f}: {e}")

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    combined['Date'] = pd.to_datetime(combined['Date'])
    combined = combined.drop_duplicates()
    return combined.sort_values('Date')


def load_meals():
    """Load all meal CSVs."""
    files = glob.glob(str(CSV_FOLDER / "meals_*.csv"))
    if not files:
        return pd.DataFrame()

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"⚠️  Error reading {f}: {e}")

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    combined['Date'] = pd.to_datetime(combined['Date'])
    combined = combined.drop_duplicates()
    return combined.sort_values('Date')


def load_body_stats():
    """Load all body stats CSVs."""
    files = glob.glob(str(CSV_FOLDER / "body_stats_*.csv"))
    if not files:
        return pd.DataFrame()

    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"⚠️  Error reading {f}: {e}")

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    combined['Date'] = pd.to_datetime(combined['Date'])
    combined = combined.drop_duplicates()
    return combined.sort_values('Date')


def analyze_workouts(df):
    """Analyze workout data."""
    if df.empty:
        return {}

    analysis = {
        'total_sessions': df['Date'].nunique(),
        'total_exercises': len(df),
        'total_sets': df['Sets'].sum(),
        'date_range': f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}",
        'exercises_per_session': round(len(df) / df['Date'].nunique(), 1),
        'top_exercises': df['Exercise'].value_counts().head(10).to_dict(),
        'volume_by_exercise': df.groupby('Exercise').apply(
            lambda x: (x['Weight_kg'] * x['Reps'] * x['Sets']).sum()
        ).sort_values(ascending=False).head(10).to_dict(),
        'daily_volume': df.groupby(df['Date'].dt.date).apply(
            lambda x: (x['Weight_kg'] * x['Reps'] * x['Sets']).sum()
        ).to_dict(),
    }

    # Progress tracking for key exercises
    key_exercises = ['Front Squat', 'Leg Press', 'OHP', 'Overhead Press', 'Barbell Squat']
    progress = {}
    for ex in key_exercises:
        ex_data = df[df['Exercise'].str.contains(ex, case=False, na=False)]
        if not ex_data.empty:
            progress[ex] = {
                'first_weight': ex_data.iloc[0]['Weight_kg'],
                'last_weight': ex_data.iloc[-1]['Weight_kg'],
                'max_weight': ex_data['Weight_kg'].max(),
                'sessions': len(ex_data),
            }
    analysis['progress'] = progress

    return analysis


def analyze_meals(df):
    """Analyze meal data."""
    if df.empty:
        return {}

    daily = df.groupby(df['Date'].dt.date).agg({
        'Protein_g': 'sum',
        'Calories': 'sum',
        'Meal': 'count'
    }).rename(columns={'Meal': 'Meals'})

    analysis = {
        'total_days': len(daily),
        'avg_daily_protein': round(daily['Protein_g'].mean(), 1),
        'avg_daily_calories': round(daily['Calories'].mean(), 0),
        'avg_meals_per_day': round(daily['Meals'].mean(), 1),
        'protein_goal_hit': len(daily[daily['Protein_g'] >= 160]),  # Target 160g+
        'calorie_range': f"{daily['Calories'].min():.0f} - {daily['Calories'].max():.0f}",
        'daily_data': daily.to_dict('index'),
    }

    return analysis


def analyze_body(df):
    """Analyze body stats."""
    if df.empty:
        return {}

    # Filter out rows with no weight data
    weight_data = df[df['Weight_kg'].notna()]
    bf_data = df[df['BodyFat_pct'].notna()]

    analysis = {
        'total_measurements': len(df),
        'date_range': f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}",
    }

    if not weight_data.empty:
        analysis['weight'] = {
            'start': weight_data.iloc[0]['Weight_kg'],
            'current': weight_data.iloc[-1]['Weight_kg'],
            'min': weight_data['Weight_kg'].min(),
            'max': weight_data['Weight_kg'].max(),
            'change': weight_data.iloc[-1]['Weight_kg'] - weight_data.iloc[0]['Weight_kg'],
        }

    if not bf_data.empty:
        analysis['body_fat'] = {
            'start': bf_data.iloc[0]['BodyFat_pct'],
            'current': bf_data.iloc[-1]['BodyFat_pct'],
            'change': bf_data.iloc[-1]['BodyFat_pct'] - bf_data.iloc[0]['BodyFat_pct'],
        }

    return analysis


def generate_html_report(workout_analysis, meal_analysis, body_analysis):
    """Generate beautiful HTML report."""

    today = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Build workout section
    workout_html = ""
    if workout_analysis:
        top_exercises_html = "".join([
            f'<div class="stat-row"><span>{ex}</span><span class="stat-value">{count}x</span></div>'
            for ex, count in list(workout_analysis.get('top_exercises', {}).items())[:5]
        ])

        progress_html = ""
        for ex, data in workout_analysis.get('progress', {}).items():
            change = data['last_weight'] - data['first_weight']
            change_class = 'positive' if change > 0 else 'negative' if change < 0 else ''
            progress_html += f'''
            <div class="progress-card">
                <div class="progress-title">{ex}</div>
                <div class="progress-stats">
                    <span>{data['first_weight']}kg → {data['last_weight']}kg</span>
                    <span class="change {change_class}">{'+' if change > 0 else ''}{change}kg</span>
                </div>
                <div class="progress-detail">Max: {data['max_weight']}kg • {data['sessions']} sessions</div>
            </div>
            '''

        workout_html = f'''
        <div class="section">
            <h2>🏋️ Workout Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{workout_analysis['total_sessions']}</div>
                    <div class="stat-label">Sessions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{workout_analysis['total_exercises']}</div>
                    <div class="stat-label">Exercises</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{workout_analysis['total_sets']}</div>
                    <div class="stat-label">Total Sets</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{workout_analysis['exercises_per_session']}</div>
                    <div class="stat-label">Avg/Session</div>
                </div>
            </div>
            <div class="card">
                <h3>Top Exercises</h3>
                {top_exercises_html}
            </div>
            <div class="card">
                <h3>Strength Progress</h3>
                {progress_html if progress_html else '<p class="muted">Not enough data for progress tracking</p>'}
            </div>
        </div>
        '''

    # Build meals section
    meal_html = ""
    if meal_analysis:
        protein_pct = (meal_analysis['protein_goal_hit'] / meal_analysis['total_days'] * 100) if meal_analysis['total_days'] > 0 else 0
        meal_html = f'''
        <div class="section">
            <h2>🍽️ Nutrition Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{meal_analysis['total_days']}</div>
                    <div class="stat-label">Days Tracked</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{meal_analysis['avg_daily_protein']}g</div>
                    <div class="stat-label">Avg Protein</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{meal_analysis['avg_daily_calories']:.0f}</div>
                    <div class="stat-label">Avg Calories</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{protein_pct:.0f}%</div>
                    <div class="stat-label">Protein Goal (160g+)</div>
                </div>
            </div>
            <div class="card">
                <h3>Daily Targets</h3>
                <div class="target-bar">
                    <div class="target-label">Protein (160-180g)</div>
                    <div class="bar-container">
                        <div class="bar" style="width: {min(100, meal_analysis['avg_daily_protein']/180*100)}%; background: {'#10b981' if meal_analysis['avg_daily_protein'] >= 160 else '#f59e0b'}"></div>
                    </div>
                    <span>{meal_analysis['avg_daily_protein']}g</span>
                </div>
                <div class="target-bar">
                    <div class="target-label">Calories (2000-2200)</div>
                    <div class="bar-container">
                        <div class="bar" style="width: {min(100, meal_analysis['avg_daily_calories']/2200*100)}%; background: {'#10b981' if 1900 <= meal_analysis['avg_daily_calories'] <= 2300 else '#f59e0b'}"></div>
                    </div>
                    <span>{meal_analysis['avg_daily_calories']:.0f}</span>
                </div>
            </div>
        </div>
        '''

    # Build body section
    body_html = ""
    if body_analysis and 'weight' in body_analysis:
        weight = body_analysis['weight']
        change_class = 'negative' if weight['change'] < 0 else 'positive' if weight['change'] > 0 else ''

        bf_html = ""
        if 'body_fat' in body_analysis:
            bf = body_analysis['body_fat']
            bf_change_class = 'negative' if bf['change'] < 0 else 'positive'
            bf_html = f'''
            <div class="stat-card">
                <div class="stat-number">{bf['current']}%</div>
                <div class="stat-label">Body Fat</div>
                <div class="change {bf_change_class}">{'+' if bf['change'] > 0 else ''}{bf['change']:.1f}%</div>
            </div>
            '''

        body_html = f'''
        <div class="section">
            <h2>📏 Body Composition</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{weight['current']}kg</div>
                    <div class="stat-label">Current Weight</div>
                    <div class="change {change_class}">{'+' if weight['change'] > 0 else ''}{weight['change']:.1f}kg</div>
                </div>
                {bf_html}
                <div class="stat-card">
                    <div class="stat-number">{body_analysis['total_measurements']}</div>
                    <div class="stat-label">Measurements</div>
                </div>
            </div>
        </div>
        '''

    # Full HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fitness Report - {today}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #f1f5f9;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #3b82f6, #06b6d4);
            border-radius: 16px;
            margin-bottom: 25px;
        }}
        .header h1 {{ font-size: 2rem; margin-bottom: 5px; }}
        .header .date {{ opacity: 0.9; font-size: 0.9rem; }}
        .section {{
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .section h2 {{
            font-size: 1.3rem;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #334155;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: #0f172a;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 1.8rem;
            font-weight: 700;
            color: #3b82f6;
        }}
        .stat-label {{
            font-size: 0.8rem;
            color: #94a3b8;
            margin-top: 5px;
        }}
        .card {{
            background: #0f172a;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }}
        .card h3 {{
            font-size: 1rem;
            margin-bottom: 12px;
            color: #60a5fa;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #1e293b;
        }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-value {{ color: #3b82f6; font-weight: 600; }}
        .progress-card {{
            background: #1e293b;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
        }}
        .progress-title {{ font-weight: 600; margin-bottom: 5px; }}
        .progress-stats {{
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
        }}
        .progress-detail {{
            font-size: 0.8rem;
            color: #94a3b8;
            margin-top: 5px;
        }}
        .change {{
            font-weight: 600;
            font-size: 0.85rem;
        }}
        .change.positive {{ color: #10b981; }}
        .change.negative {{ color: #ef4444; }}
        .target-bar {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }}
        .target-label {{
            width: 140px;
            font-size: 0.85rem;
            color: #94a3b8;
        }}
        .bar-container {{
            flex: 1;
            height: 8px;
            background: #334155;
            border-radius: 4px;
            overflow: hidden;
        }}
        .bar {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }}
        .muted {{ color: #64748b; font-style: italic; }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #64748b;
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Fitness Progress Report</h1>
            <div class="date">Generated: {today}</div>
        </div>

        {body_html}
        {workout_html}
        {meal_html}

        <div class="footer">
            <p>Generated by Fitness Analyzer • Data from fitness_tracker.html</p>
        </div>
    </div>
</body>
</html>'''

    return html


def main():
    print("=" * 50)
    print("📊 Fitness Data Analyzer")
    print("=" * 50)

    ensure_folders()

    # Check for CSV files
    csv_files = list(CSV_FOLDER.glob("*.csv"))
    if not csv_files:
        print(f"\n⚠️  No CSV files found in {CSV_FOLDER}")
        print("\nTo use this analyzer:")
        print("1. Export CSVs from fitness_tracker.html on your phone")
        print("2. AirDrop them to this Mac")
        print(f"3. Move them to: {CSV_FOLDER}")
        print("4. Run this script again")
        return

    print(f"\n📄 Found {len(csv_files)} CSV files")

    # Load data
    print("\n🔄 Loading data...")
    workouts = load_workouts()
    meals = load_meals()
    body = load_body_stats()

    print(f"   Workouts: {len(workouts)} entries")
    print(f"   Meals: {len(meals)} entries")
    print(f"   Body stats: {len(body)} entries")

    # Analyze
    print("\n📈 Analyzing...")
    workout_analysis = analyze_workouts(workouts)
    meal_analysis = analyze_meals(meals)
    body_analysis = analyze_body(body)

    # Generate report
    print("\n📝 Generating report...")
    html = generate_html_report(workout_analysis, meal_analysis, body_analysis)

    report_file = REPORT_FOLDER / f"fitness_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(report_file, 'w') as f:
        f.write(html)

    print(f"\n✅ Report saved: {report_file}")
    print("\n🌐 Opening in browser...")
    os.system(f'open "{report_file}"')


if __name__ == "__main__":
    main()
