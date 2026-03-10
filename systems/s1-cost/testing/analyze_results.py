"""Analysis and visualization script for compression benchmark results."""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse

def load_results(results_dir: str = "benchmark_results") -> dict:
    """Load benchmark results from JSON file."""
    results_path = Path(results_dir) / "comprehensive_benchmark_results.json"
    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found: {results_path}")

    with open(results_path, 'r') as f:
        return json.load(f)

def create_comparison_dataframe(results: dict) -> pd.DataFrame:
    """Create DataFrame for easy analysis."""
    data = []

    for strategy_name, strategy_data in results["strategies"].items():
        metrics = strategy_data.get("performance_metrics", {})
        if metrics:
            data.append({
                "Strategy": strategy_name.replace('_', ' ').title(),
                "Compression Ratio": metrics.get("average_compression_ratio", 1.0),
                "Compression Savings (%)": metrics.get("compression_savings_percent", 0.0),
                "Processing Time (s)": metrics.get("average_processing_time", 0.0),
                "Success Rate (%)": metrics.get("success_rate_percent", 0.0),
                "Effectiveness Score": metrics.get("effectiveness_score", 1.0),
                "Total Tests": strategy_data.get("total_tests", 0),
                "Successful Tests": strategy_data.get("successful_tests", 0)
            })

    return pd.DataFrame(data)

def create_visualizations(df: pd.DataFrame, output_dir: str = "benchmark_results"):
    """Create comprehensive visualizations."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Set style
    plt.style.use('seaborn-v0_8')
    fig_size = (14, 10)

    # 1. Compression Savings Comparison
    plt.figure(figsize=fig_size)
    plt.subplot(2, 3, 1)
    bars = plt.bar(range(len(df)), df["Compression Savings (%)"],
                   color=plt.cm.viridis(df["Compression Savings (%)"] / df["Compression Savings (%)"].max()))
    plt.xlabel("Strategy")
    plt.ylabel("Compression Savings (%)")
    plt.title("Compression Effectiveness")
    plt.xticks(range(len(df)), df["Strategy"], rotation=45, ha='right')

    # Add value labels on bars
    for i, bar in enumerate(bars):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{df.iloc[i]["Compression Savings (%)"]:.1f}%',
                ha='center', va='bottom', fontsize=8)

    # 2. Processing Speed Comparison
    plt.subplot(2, 3, 2)
    bars = plt.bar(range(len(df)), df["Processing Time (s)"],
                   color=plt.cm.plasma(1 - df["Processing Time (s)"] / df["Processing Time (s)"].max()))
    plt.xlabel("Strategy")
    plt.ylabel("Processing Time (s)")
    plt.title("Processing Speed")
    plt.xticks(range(len(df)), df["Strategy"], rotation=45, ha='right')

    # 3. Success Rate Comparison
    plt.subplot(2, 3, 3)
    bars = plt.bar(range(len(df)), df["Success Rate (%)"],
                   color=plt.cm.RdYlGn(df["Success Rate (%)"] / 100))
    plt.xlabel("Strategy")
    plt.ylabel("Success Rate (%)")
    plt.title("Reliability")
    plt.xticks(range(len(df)), df["Strategy"], rotation=45, ha='right')
    plt.ylim(0, 105)

    # 4. Effectiveness Score (lower is better)
    plt.subplot(2, 3, 4)
    bars = plt.bar(range(len(df)), df["Effectiveness Score"],
                   color=plt.cm.RdYlBu_r(df["Effectiveness Score"] / df["Effectiveness Score"].max()))
    plt.xlabel("Strategy")
    plt.ylabel("Effectiveness Score")
    plt.title("Overall Effectiveness (Lower = Better)")
    plt.xticks(range(len(df)), df["Strategy"], rotation=45, ha='right')

    # 5. Scatter plot: Compression vs Speed
    plt.subplot(2, 3, 5)
    scatter = plt.scatter(df["Processing Time (s)"], df["Compression Savings (%)"],
                         c=df["Success Rate (%)"], cmap='RdYlGn', s=100, alpha=0.7)
    plt.xlabel("Processing Time (s)")
    plt.ylabel("Compression Savings (%)")
    plt.title("Compression vs Speed (Color = Success Rate)")
    plt.colorbar(scatter, label="Success Rate (%)")

    # Add strategy labels
    for i, txt in enumerate(df["Strategy"]):
        plt.annotate(txt, (df.iloc[i]["Processing Time (s)"],
                          df.iloc[i]["Compression Savings (%)"]),
                    xytext=(5, 5), textcoords='offset points', fontsize=8)

    # 6. Radar chart for top 3 strategies
    plt.subplot(2, 3, 6)

    # Select top 3 by effectiveness score
    top_3 = df.nsmallest(3, "Effectiveness Score")

    metrics = ["Compression Savings (%)", "Success Rate (%)", "Processing Speed Rank"]

    # Normalize processing time (invert so higher is better)
    processing_speed_rank = (1 / df["Processing Time (s)"]) * 100
    top_3_speed_rank = processing_speed_rank[top_3.index]

    angles = [i * 2 * 3.14159 / len(metrics) for i in range(len(metrics))]
    angles += angles[:1]  # Complete the circle

    for idx, (_, strategy) in enumerate(top_3.iterrows()):
        values = [
            strategy["Compression Savings (%)"],
            strategy["Success Rate (%)"],
            top_3_speed_rank.iloc[idx]
        ]
        values += values[:1]  # Complete the circle

        plt.polar(angles, values, 'o-', linewidth=2, label=strategy["Strategy"])
        plt.fill(angles, values, alpha=0.25)

    plt.xticks(angles[:-1], metrics)
    plt.title("Top 3 Strategies Comparison")
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

    plt.tight_layout()
    plt.savefig(output_path / "compression_benchmark_analysis.png", dpi=300, bbox_inches='tight')
    plt.show()

    # Create heatmap for detailed comparison
    plt.figure(figsize=(12, 8))

    # Prepare data for heatmap (normalize metrics for better visualization)
    heatmap_data = df.set_index("Strategy")[
        ["Compression Savings (%)", "Processing Time (s)", "Success Rate (%)", "Effectiveness Score"]
    ].copy()

    # Normalize each column to 0-1 scale for heatmap
    for col in heatmap_data.columns:
        if col == "Processing Time (s)" or col == "Effectiveness Score":
            # For these metrics, lower is better, so invert
            heatmap_data[col] = 1 - (heatmap_data[col] - heatmap_data[col].min()) / (heatmap_data[col].max() - heatmap_data[col].min())
        else:
            # For these metrics, higher is better
            heatmap_data[col] = (heatmap_data[col] - heatmap_data[col].min()) / (heatmap_data[col].max() - heatmap_data[col].min())

    sns.heatmap(heatmap_data.T, annot=True, cmap='RdYlGn', cbar_kws={'label': 'Normalized Performance (1.0 = Best)'})
    plt.title("Strategy Performance Heatmap\n(Normalized: 1.0 = Best Performance)")
    plt.xlabel("Strategy")
    plt.ylabel("Metric")
    plt.tight_layout()
    plt.savefig(output_path / "strategy_heatmap.png", dpi=300, bbox_inches='tight')
    plt.show()

def generate_detailed_report(results: dict, df: pd.DataFrame, output_dir: str = "benchmark_results"):
    """Generate detailed markdown report."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    report_path = output_path / "benchmark_report.md"

    with open(report_path, 'w') as f:
        f.write("# Compression Strategy Benchmark Report\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")
        summary = results.get("summary", {})

        f.write(f"**Best Compression**: {summary['best_compression']['strategy']} "
                f"({summary['best_compression']['savings_percent']:.1f}% savings)\n\n")
        f.write(f"**Fastest Processing**: {summary['fastest_processing']['strategy']} "
                f"({summary['fastest_processing']['time']:.3f}s average)\n\n")
        f.write(f"**Most Reliable**: {summary['most_reliable']['strategy']} "
                f"({summary['most_reliable']['success_rate']:.1f}% success rate)\n\n")
        f.write(f"**Best Overall**: {summary['best_overall']['strategy']} "
                f"(effectiveness score: {summary['best_overall']['score']:.3f})\n\n")

        # Strategy Rankings Table
        f.write("## Strategy Rankings\n\n")
        f.write("| Rank | Strategy | Compression Savings | Processing Time | Success Rate | Effectiveness Score |\n")
        f.write("|------|----------|-------------------|----------------|-------------|-------------------|\n")

        for i, row in df.sort_values("Effectiveness Score").iterrows():
            rank = df.sort_values("Effectiveness Score").index.get_loc(i) + 1
            f.write(f"| {rank} | {row['Strategy']} | {row['Compression Savings (%)']:.1f}% | "
                    f"{row['Processing Time (s)']:.3f}s | {row['Success Rate (%)']:.1f}% | "
                    f"{row['Effectiveness Score']:.3f} |\n")

        # Recommendations
        f.write("\n## Recommendations\n\n")
        recommendations = results.get("recommendations", {})

        for key, recommendation in recommendations.items():
            if key != "use_cases":
                f.write(f"**{key.replace('_', ' ').title()}**: {recommendation}\n\n")

        f.write("### Use Case Recommendations\n\n")
        use_cases = recommendations.get("use_cases", {})
        for use_case, strategy in use_cases.items():
            f.write(f"- **{use_case.replace('_', ' ').title()}**: {strategy}\n")

        # Detailed Analysis
        f.write("\n## Detailed Analysis\n\n")

        # Best performers in each category
        best_compression = df.loc[df["Compression Savings (%)"].idxmax()]
        fastest_processing = df.loc[df["Processing Time (s)"].idxmin()]
        most_reliable = df.loc[df["Success Rate (%)"].idxmax()]

        f.write(f"### Compression Leaders\n")
        f.write(f"1. **{best_compression['Strategy']}**: {best_compression['Compression Savings (%)']:.1f}% savings\n")
        f.write(f"   - Success Rate: {best_compression['Success Rate (%)']:.1f}%\n")
        f.write(f"   - Processing Time: {best_compression['Processing Time (s)']:.3f}s\n\n")

        f.write(f"### Speed Leaders\n")
        f.write(f"1. **{fastest_processing['Strategy']}**: {fastest_processing['Processing Time (s)']:.3f}s average\n")
        f.write(f"   - Compression: {fastest_processing['Compression Savings (%)']:.1f}% savings\n")
        f.write(f"   - Success Rate: {fastest_processing['Success Rate (%)']:.1f}%\n\n")

        f.write(f"### Reliability Leaders\n")
        f.write(f"1. **{most_reliable['Strategy']}**: {most_reliable['Success Rate (%)']:.1f}% success rate\n")
        f.write(f"   - Compression: {most_reliable['Compression Savings (%)']:.1f}% savings\n")
        f.write(f"   - Processing Time: {most_reliable['Processing Time (s)']:.3f}s\n\n")

    print(f"📄 Detailed report saved to: {report_path}")

def main():
    """Main analysis function."""
    parser = argparse.ArgumentParser(description="Analyze compression benchmark results")
    parser.add_argument("--results-dir", default="benchmark_results",
                       help="Directory containing benchmark results")
    parser.add_argument("--no-viz", action="store_true",
                       help="Skip visualization generation")

    args = parser.parse_args()

    try:
        # Load results
        print("📊 Loading benchmark results...")
        results = load_results(args.results_dir)

        # Create DataFrame
        df = create_comparison_dataframe(results)
        print(f"📈 Loaded data for {len(df)} strategies")

        # Generate visualizations
        if not args.no_viz:
            print("🎨 Creating visualizations...")
            create_visualizations(df, args.results_dir)

        # Generate report
        print("📝 Generating detailed report...")
        generate_detailed_report(results, df, args.results_dir)

        # Print summary stats
        print("\n" + "="*60)
        print("BENCHMARK ANALYSIS SUMMARY")
        print("="*60)

        print(f"\n🏆 Top 3 Strategies by Overall Effectiveness:")
        top_3 = df.nsmallest(3, "Effectiveness Score")
        for i, (_, row) in enumerate(top_3.iterrows(), 1):
            print(f"  {i}. {row['Strategy']:<25} (Score: {row['Effectiveness Score']:.3f})")

        print(f"\n💾 Compression Champions:")
        print(f"  Best: {df.loc[df['Compression Savings (%)'].idxmax(), 'Strategy']:<25} "
              f"({df['Compression Savings (%)'].max():.1f}% savings)")
        print(f"  Avg:  {df['Compression Savings (%)'].mean():.1f}% savings")

        print(f"\n⚡ Speed Champions:")
        print(f"  Best: {df.loc[df['Processing Time (s)'].idxmin(), 'Strategy']:<25} "
              f"({df['Processing Time (s)'].min():.3f}s)")
        print(f"  Avg:  {df['Processing Time (s)'].mean():.3f}s")

        print(f"\n🎯 Reliability Champions:")
        print(f"  Best: {df.loc[df['Success Rate (%)'].idxmax(), 'Strategy']:<25} "
              f"({df['Success Rate (%)'].max():.1f}%)")
        print(f"  Avg:  {df['Success Rate (%)'].mean():.1f}%")

        print(f"\n✅ Analysis completed successfully!")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())