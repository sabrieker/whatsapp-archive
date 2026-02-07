"""
Analytics service for generating chat visualizations.
Adapted from whatsapp-heatmap project, optimized for long-running chats (5+ years).
"""

import io
import logging
from datetime import datetime
from typing import Optional
from collections import defaultdict

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
import calplot

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Message, Participant, Conversation
from .storage import StorageService

logger = logging.getLogger(__name__)

# Style settings
plt.style.use('seaborn-v0_8-whitegrid')
FONT_SIZE_TITLE = 14
FONT_SIZE_LABEL = 11
FONT_SIZE_TICK = 9


class AnalyticsService:
    """Generate analytics visualizations for conversations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = StorageService()

    async def get_message_data(self, conversation_id: int) -> pd.DataFrame:
        """Fetch messages and convert to DataFrame for analysis."""
        stmt = (
            select(
                Message.timestamp,
                Message.sender_name,
                Message.participant_id,
            )
            .where(Message.conversation_id == conversation_id)
            .where(Message.message_type != 'system')
            .order_by(Message.timestamp)
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=['datetime', 'sender', 'participant_id'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['date'] = df['datetime'].dt.date
        df['hour'] = df['datetime'].dt.hour
        df['day_of_week'] = df['datetime'].dt.dayofweek
        df['day_name'] = df['datetime'].dt.day_name()
        df['month'] = df['datetime'].dt.to_period('M')
        df['year'] = df['datetime'].dt.year
        df['quarter'] = df['datetime'].dt.to_period('Q')

        return df

    async def get_participants(self, conversation_id: int) -> list[dict]:
        """Get participants with their colors."""
        stmt = (
            select(Participant)
            .where(Participant.conversation_id == conversation_id)
            .order_by(Participant.message_count.desc())
        )
        result = await self.db.execute(stmt)
        participants = result.scalars().all()

        return [
            {"id": p.id, "name": p.name, "color": p.color, "message_count": p.message_count}
            for p in participants
        ]

    async def generate_analytics(
        self,
        conversation_id: int,
        person1: Optional[str] = None,
        person2: Optional[str] = None,
    ) -> dict:
        """Generate all analytics charts and return URLs.

        If person1 and person2 are provided, generates comparison charts.
        Otherwise, generates group-wide analytics.
        """
        df = await self.get_message_data(conversation_id)

        if df.empty:
            raise ValueError("No messages found for analysis")

        participants = await self.get_participants(conversation_id)

        # Check if we're doing a comparison or group analytics
        do_comparison = bool(person1 and person2)

        # Generate all charts
        charts = {}
        storage_prefix = f"conversations/{conversation_id}/analytics"

        # Calculate date range for adaptive sizing
        years_span = float((df['datetime'].max() - df['datetime'].min()).days / 365)

        # 1. Time heatmap (hour x day of week) - always show overall
        img_data = self._create_time_heatmap(df, person1 if do_comparison else None,
                                              person2 if do_comparison else None, participants)
        key = f"{storage_prefix}/heatmap_time.png"
        self.storage.upload_bytes(key, img_data, "image/png")
        charts['time_heatmap'] = self.storage.get_presigned_url(key, expires_hours=24)

        # 2. Calendar heatmap (split by year for long chats)
        calendar_urls = self._create_calendar_heatmaps(df, storage_prefix, years_span)
        charts['calendar_heatmaps'] = calendar_urls

        # 3. Comparison heatmap (only if comparing two people)
        if do_comparison:
            img_data = self._create_comparison_heatmap(df, person1, person2, participants)
            if img_data:
                key = f"{storage_prefix}/heatmap_comparison.png"
                self.storage.upload_bytes(key, img_data, "image/png")
                charts['comparison_heatmap'] = self.storage.get_presigned_url(key, expires_hours=24)

        # 4. Monthly/Quarterly trend (adaptive based on date range)
        img_data = self._create_trend_chart(df, person1 if do_comparison else None,
                                            person2 if do_comparison else None, participants, years_span)
        key = f"{storage_prefix}/trend.png"
        self.storage.upload_bytes(key, img_data, "image/png")
        charts['trend'] = self.storage.get_presigned_url(key, expires_hours=24)

        # 5. Response time analysis (only for comparison)
        if do_comparison:
            img_data = self._create_response_time_chart(df, person1, person2, participants)
            if img_data:
                key = f"{storage_prefix}/response_time.png"
                self.storage.upload_bytes(key, img_data, "image/png")
                charts['response_time'] = self.storage.get_presigned_url(key, expires_hours=24)

        # 6. Daily activity chart
        img_data = self._create_daily_activity_chart(df, years_span)
        key = f"{storage_prefix}/daily_activity.png"
        self.storage.upload_bytes(key, img_data, "image/png")
        charts['daily_activity'] = self.storage.get_presigned_url(key, expires_hours=24)

        # 7. Top participants chart (for group chats)
        img_data = self._create_top_participants_chart(df, participants)
        key = f"{storage_prefix}/top_participants.png"
        self.storage.upload_bytes(key, img_data, "image/png")
        charts['top_participants'] = self.storage.get_presigned_url(key, expires_hours=24)

        # 8. Participation over time (who was most active each period)
        img_data = self._create_participation_over_time(df, participants, years_span)
        key = f"{storage_prefix}/participation_over_time.png"
        self.storage.upload_bytes(key, img_data, "image/png")
        charts['participation_over_time'] = self.storage.get_presigned_url(key, expires_hours=24)

        # Calculate summary stats
        summary = self._calculate_summary(df, person1 if do_comparison else None,
                                          person2 if do_comparison else None, participants)

        # Ensure all values are JSON-serializable (convert numpy types)
        result = {
            "charts": charts,
            "summary": summary,
            "participants": participants[:10],  # Top 10
            "generated_at": datetime.utcnow().isoformat(),
            "is_group_chat": len(participants) > 2,
        }
        result = self._to_native_types(result)

        # Save result to storage for caching
        self._save_analytics_result(conversation_id, result)

        return result

    def _save_analytics_result(self, conversation_id: int, result: dict) -> None:
        """Save analytics result to MinIO for caching."""
        import json
        key = f"conversations/{conversation_id}/analytics/result.json"
        data = json.dumps(result, ensure_ascii=False).encode('utf-8')
        self.storage.upload_bytes(key, data, "application/json")

    def get_cached_analytics(self, conversation_id: int) -> Optional[dict]:
        """Get cached analytics result if it exists."""
        import json
        key = f"conversations/{conversation_id}/analytics/result.json"
        try:
            data = self.storage.download_bytes(key)
            if data:
                result = json.loads(data.decode('utf-8'))
                # Refresh presigned URLs (they expire)
                result = self._refresh_chart_urls(conversation_id, result)
                return result
        except Exception as e:
            logger.debug(f"No cached analytics for conversation {conversation_id}: {e}")
        return None

    def _refresh_chart_urls(self, conversation_id: int, result: dict) -> dict:
        """Refresh presigned URLs for charts."""
        storage_prefix = f"conversations/{conversation_id}/analytics"

        # Refresh main chart URLs
        chart_keys = {
            'time_heatmap': 'heatmap_time.png',
            'trend': 'trend.png',
            'daily_activity': 'daily_activity.png',
            'top_participants': 'top_participants.png',
            'participation_over_time': 'participation_over_time.png',
            'comparison_heatmap': 'heatmap_comparison.png',
            'response_time': 'response_time.png',
        }

        for chart_name, filename in chart_keys.items():
            if chart_name in result.get('charts', {}):
                key = f"{storage_prefix}/{filename}"
                try:
                    result['charts'][chart_name] = self.storage.get_presigned_url(key, expires_hours=24)
                except:
                    pass

        # Refresh calendar heatmap URLs
        if 'calendar_heatmaps' in result.get('charts', {}):
            for cal in result['charts']['calendar_heatmaps']:
                year = cal.get('year', 'all')
                key = f"{storage_prefix}/calendar_{year}.png"
                try:
                    cal['url'] = self.storage.get_presigned_url(key, expires_hours=24)
                except:
                    pass

        return result

    def _get_participant_color(self, name: str, participants: list[dict]) -> str:
        """Get color for a participant."""
        for p in participants:
            if p['name'].lower() == name.lower():
                return p['color']
        return '#128C7E'

    def _to_native_types(self, obj):
        """Convert numpy/pandas types to Python native types for JSON serialization."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return {str(k): self._to_native_types(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._to_native_types(item) for item in obj]
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return [self._to_native_types(item) for item in obj.tolist()]
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        if isinstance(obj, pd.Period):
            return str(obj)
        # Check for any remaining numpy generic type
        if hasattr(obj, 'item'):
            return obj.item()
        return obj

    def _create_time_heatmap(
        self,
        df: pd.DataFrame,
        person1: Optional[str],
        person2: Optional[str],
        participants: list[dict],
    ) -> bytes:
        """Create hour x day of week heatmap."""
        num_plots = 1 + (1 if person1 else 0) + (1 if person2 else 0)
        fig, axes = plt.subplots(1, num_plots, figsize=(6 * num_plots, 5))

        if num_plots == 1:
            axes = [axes]

        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        # Combined heatmap
        pivot = df.pivot_table(
            index='day_name', columns='hour', values='datetime',
            aggfunc='count', fill_value=0
        )
        pivot = pivot.reindex(day_order)

        sns.heatmap(pivot, ax=axes[0], cmap='YlOrRd', annot=False,
                    cbar_kws={'label': 'Messages'}, fmt='d')
        axes[0].set_title('All Messages', fontsize=FONT_SIZE_TITLE, fontweight='bold')
        axes[0].set_xlabel('Hour', fontsize=FONT_SIZE_LABEL)
        axes[0].set_ylabel('Day', fontsize=FONT_SIZE_LABEL)
        axes[0].tick_params(labelsize=FONT_SIZE_TICK)

        # Individual heatmaps
        plot_idx = 1
        for person in [person1, person2]:
            if person and plot_idx < num_plots:
                person_df = df[df['sender'].str.lower() == person.lower()]
                if not person_df.empty:
                    pivot = person_df.pivot_table(
                        index='day_name', columns='hour', values='datetime',
                        aggfunc='count', fill_value=0
                    )
                    pivot = pivot.reindex(day_order)

                    color = self._get_participant_color(person, participants)
                    cmap = sns.light_palette(color, as_cmap=True)

                    sns.heatmap(pivot, ax=axes[plot_idx], cmap=cmap, annot=False,
                               cbar_kws={'label': 'Messages'})
                    axes[plot_idx].set_title(f'{person}', fontsize=FONT_SIZE_TITLE, fontweight='bold')
                    axes[plot_idx].set_xlabel('Hour', fontsize=FONT_SIZE_LABEL)
                    axes[plot_idx].set_ylabel('', fontsize=FONT_SIZE_LABEL)
                    axes[plot_idx].tick_params(labelsize=FONT_SIZE_TICK)
                plot_idx += 1

        plt.tight_layout()
        return self._fig_to_bytes(fig)

    def _create_calendar_heatmaps(
        self,
        df: pd.DataFrame,
        storage_prefix: str,
        years_span: float,
    ) -> list[str]:
        """Create calendar heatmaps, split by year for long chats."""
        urls = []
        daily_counts = df.groupby('date').size()
        daily_counts.index = pd.to_datetime(daily_counts.index)

        years = sorted(df['year'].unique())

        # For very long chats, generate per-year
        if years_span > 3:
            for year in years:
                year_data = daily_counts[daily_counts.index.year == year]
                if len(year_data) < 10:
                    continue

                try:
                    fig, ax = calplot.calplot(
                        year_data,
                        cmap='YlGn',
                        colorbar=True,
                        suptitle=f'Message Activity - {year}',
                        figsize=(12, 3),
                        yearlabel_kws={'fontsize': FONT_SIZE_TITLE},
                    )

                    img_data = self._fig_to_bytes(fig)
                    key = f"{storage_prefix}/calendar_{year}.png"
                    self.storage.upload_bytes(key, img_data, "image/png")
                    urls.append({
                        "year": int(year),  # Convert numpy.int64 to Python int
                        "url": self.storage.get_presigned_url(key, expires_hours=24)
                    })
                except Exception as e:
                    logger.warning(f"Failed to generate calendar for {year}: {e}")
        else:
            # Single combined calendar
            try:
                fig, ax = calplot.calplot(
                    daily_counts,
                    cmap='YlGn',
                    colorbar=True,
                    suptitle='Message Activity',
                    figsize=(14, 2 + len(years) * 1.5),
                )
                img_data = self._fig_to_bytes(fig)
                key = f"{storage_prefix}/calendar_all.png"
                self.storage.upload_bytes(key, img_data, "image/png")
                urls.append({
                    "year": "all",
                    "url": self.storage.get_presigned_url(key, expires_hours=24)
                })
            except Exception as e:
                logger.warning(f"Failed to generate combined calendar: {e}")

        return urls

    def _create_comparison_heatmap(
        self,
        df: pd.DataFrame,
        person1: str,
        person2: str,
        participants: list[dict],
    ) -> Optional[bytes]:
        """Create who-dominates-when comparison heatmap."""
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        df1 = df[df['sender'].str.lower() == person1.lower()]
        df2 = df[df['sender'].str.lower() == person2.lower()]

        if df1.empty or df2.empty:
            return None

        pivot1 = df1.pivot_table(
            index='day_name', columns='hour', values='datetime',
            aggfunc='count', fill_value=0
        ).reindex(day_order).fillna(0)

        pivot2 = df2.pivot_table(
            index='day_name', columns='hour', values='datetime',
            aggfunc='count', fill_value=0
        ).reindex(day_order).fillna(0)

        # Ensure same columns
        for h in range(24):
            if h not in pivot1.columns:
                pivot1[h] = 0
            if h not in pivot2.columns:
                pivot2[h] = 0
        pivot1 = pivot1[sorted(pivot1.columns)]
        pivot2 = pivot2[sorted(pivot2.columns)]

        total = pivot1 + pivot2
        ratio = (pivot1 - pivot2) / total.replace(0, np.nan)
        ratio = ratio.fillna(0)

        fig, ax = plt.subplots(figsize=(14, 5))

        color1 = self._get_participant_color(person1, participants)
        color2 = self._get_participant_color(person2, participants)
        colors = [color2, '#ffffff', color1]
        cmap = LinearSegmentedColormap.from_list('custom', colors)

        sns.heatmap(ratio, ax=ax, cmap=cmap, center=0, vmin=-1, vmax=1,
                   cbar_kws={'label': f'← {person2} | {person1} →'})

        ax.set_title(f'Who Messages More at Each Time', fontsize=FONT_SIZE_TITLE, fontweight='bold')
        ax.set_xlabel('Hour', fontsize=FONT_SIZE_LABEL)
        ax.set_ylabel('Day', fontsize=FONT_SIZE_LABEL)
        ax.tick_params(labelsize=FONT_SIZE_TICK)

        plt.tight_layout()
        return self._fig_to_bytes(fig)

    def _create_trend_chart(
        self,
        df: pd.DataFrame,
        person1: Optional[str],
        person2: Optional[str],
        participants: list[dict],
        years_span: float,
    ) -> bytes:
        """Create trend chart - monthly for short chats, quarterly/yearly for long ones."""
        fig, ax = plt.subplots(figsize=(max(12, years_span * 2), 5))

        # Choose aggregation based on time span
        if years_span > 5:
            # Quarterly for very long chats
            period_col = 'quarter'
            title = 'Quarterly Message Volume'
        elif years_span > 2:
            # Quarterly
            period_col = 'quarter'
            title = 'Quarterly Message Volume'
        else:
            # Monthly
            period_col = 'month'
            title = 'Monthly Message Volume'

        # Get top participants to show
        top_senders = df['sender'].value_counts().head(5).index.tolist()

        # Aggregate
        trend = df[df['sender'].isin(top_senders)].groupby(
            [df[period_col], 'sender']
        ).size().unstack(fill_value=0)

        # Sort columns by total
        col_order = trend.sum().sort_values(ascending=False).index
        trend = trend[col_order]

        trend.index = trend.index.astype(str)

        # Use participant colors
        colors = [self._get_participant_color(name, participants) for name in trend.columns]

        trend.plot(kind='bar', ax=ax, width=0.8, color=colors, edgecolor='none')

        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight='bold')
        ax.set_xlabel('')
        ax.set_ylabel('Messages', fontsize=FONT_SIZE_LABEL)
        ax.legend(title='', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=FONT_SIZE_TICK)

        # Smart x-axis labels
        n_ticks = len(trend.index)
        if n_ticks > 20:
            # Show every Nth label
            step = max(1, n_ticks // 15)
            for i, label in enumerate(ax.xaxis.get_ticklabels()):
                if i % step != 0:
                    label.set_visible(False)

        plt.xticks(rotation=45, ha='right', fontsize=FONT_SIZE_TICK)
        plt.yticks(fontsize=FONT_SIZE_TICK)
        plt.tight_layout()

        return self._fig_to_bytes(fig)

    def _create_response_time_chart(
        self,
        df: pd.DataFrame,
        person1: str,
        person2: str,
        participants: list[dict],
    ) -> Optional[bytes]:
        """Create response time analysis chart."""
        df_sorted = df.sort_values('datetime').copy()

        df_sorted['prev_sender'] = df_sorted['sender'].shift(1)
        df_sorted['prev_time'] = df_sorted['datetime'].shift(1)
        df_sorted['response_time'] = (
            df_sorted['datetime'] - df_sorted['prev_time']
        ).dt.total_seconds() / 60

        # Only count actual responses
        df_sorted = df_sorted[
            (df_sorted['sender'] != df_sorted['prev_sender']) &
            (df_sorted['response_time'] < 24 * 60) &
            (df_sorted['response_time'] > 0)
        ]

        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        for idx, person in enumerate([person1, person2]):
            person_df = df_sorted[df_sorted['sender'].str.lower() == person.lower()]
            if person_df.empty:
                continue

            avg_response = person_df.groupby('hour')['response_time'].mean()
            hours = range(24)
            values = [avg_response.get(h, 0) for h in hours]

            color = self._get_participant_color(person, participants)
            axes[idx].bar(hours, values, color=color, alpha=0.8)
            axes[idx].set_title(f'{person}\'s Avg Response Time', fontsize=FONT_SIZE_TITLE, fontweight='bold')
            axes[idx].set_xlabel('Hour', fontsize=FONT_SIZE_LABEL)
            axes[idx].set_ylabel('Minutes', fontsize=FONT_SIZE_LABEL)
            axes[idx].set_xticks(range(0, 24, 3))
            axes[idx].tick_params(labelsize=FONT_SIZE_TICK)

        plt.tight_layout()
        return self._fig_to_bytes(fig)

    def _create_daily_activity_chart(self, df: pd.DataFrame, years_span: float) -> bytes:
        """Create daily activity overview with rolling average."""
        daily = df.groupby('date').size().reset_index(name='count')
        daily['date'] = pd.to_datetime(daily['date'])
        daily = daily.sort_values('date')

        fig, ax = plt.subplots(figsize=(max(12, years_span * 2), 4))

        # Rolling average window based on time span
        window = min(30, max(7, int(years_span * 5)))
        daily['rolling'] = daily['count'].rolling(window=window, center=True).mean()

        ax.fill_between(daily['date'], daily['count'], alpha=0.3, color='#3498db', label='Daily')
        ax.plot(daily['date'], daily['rolling'], color='#e74c3c', linewidth=2, label=f'{window}-day avg')
        ax.axhline(y=daily['count'].mean(), color='#2ecc71', linestyle='--',
                   label=f'Overall avg: {daily["count"].mean():.1f}/day')

        ax.set_title('Daily Message Activity', fontsize=FONT_SIZE_TITLE, fontweight='bold')
        ax.set_xlabel('')
        ax.set_ylabel('Messages', fontsize=FONT_SIZE_LABEL)
        ax.legend(loc='upper right', fontsize=FONT_SIZE_TICK)
        ax.tick_params(labelsize=FONT_SIZE_TICK)

        # Format x-axis for long time spans
        if years_span > 3:
            ax.xaxis.set_major_locator(plt.matplotlib.dates.YearLocator())
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y'))

        plt.tight_layout()
        return self._fig_to_bytes(fig)

    def _create_top_participants_chart(
        self,
        df: pd.DataFrame,
        participants: list[dict],
    ) -> bytes:
        """Create bar chart of top participants by message count."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Get top 10 senders
        top_senders = df['sender'].value_counts().head(10)

        # Bar chart
        colors = [self._get_participant_color(name, participants) for name in top_senders.index]
        bars = axes[0].barh(range(len(top_senders)), top_senders.values, color=colors)
        axes[0].set_yticks(range(len(top_senders)))
        axes[0].set_yticklabels(top_senders.index, fontsize=FONT_SIZE_TICK)
        axes[0].invert_yaxis()
        axes[0].set_xlabel('Messages', fontsize=FONT_SIZE_LABEL)
        axes[0].set_title('Top Participants', fontsize=FONT_SIZE_TITLE, fontweight='bold')

        # Add count labels
        for i, (count, bar) in enumerate(zip(top_senders.values, bars)):
            axes[0].text(count + max(top_senders.values) * 0.01, i,
                        f'{count:,}', va='center', fontsize=FONT_SIZE_TICK)

        # Pie chart of participation share
        total = len(df)
        top_5 = df['sender'].value_counts().head(5)
        others = total - top_5.sum()

        pie_labels = list(top_5.index) + (['Others'] if others > 0 else [])
        pie_values = list(top_5.values) + ([others] if others > 0 else [])
        pie_colors = [self._get_participant_color(name, participants) for name in top_5.index]
        if others > 0:
            pie_colors.append('#cccccc')

        axes[1].pie(pie_values, labels=pie_labels, colors=pie_colors, autopct='%1.1f%%',
                   textprops={'fontsize': FONT_SIZE_TICK})
        axes[1].set_title('Message Share', fontsize=FONT_SIZE_TITLE, fontweight='bold')

        plt.tight_layout()
        return self._fig_to_bytes(fig)

    def _create_participation_over_time(
        self,
        df: pd.DataFrame,
        participants: list[dict],
        years_span: float,
    ) -> bytes:
        """Create stacked area chart showing participation over time."""
        fig, ax = plt.subplots(figsize=(max(12, years_span * 2), 5))

        # Choose aggregation based on time span
        if years_span > 3:
            period_col = 'quarter'
            title = 'Participation Over Time (Quarterly)'
        else:
            period_col = 'month'
            title = 'Participation Over Time (Monthly)'

        # Get top 6 senders + Others
        top_senders = df['sender'].value_counts().head(6).index.tolist()

        # Create a copy and categorize non-top senders as "Others"
        df_copy = df.copy()
        df_copy['sender_grouped'] = df_copy['sender'].apply(
            lambda x: x if x in top_senders else 'Others'
        )

        # Aggregate
        period_sender = df_copy.groupby([df_copy[period_col], 'sender_grouped']).size().unstack(fill_value=0)

        # Sort columns by total (top first)
        col_order = period_sender.sum().sort_values(ascending=False).index
        period_sender = period_sender[col_order]

        period_sender.index = period_sender.index.astype(str)

        # Use participant colors
        colors = []
        for name in period_sender.columns:
            if name == 'Others':
                colors.append('#cccccc')
            else:
                colors.append(self._get_participant_color(name, participants))

        period_sender.plot(kind='area', stacked=True, ax=ax, color=colors, alpha=0.8)

        ax.set_title(title, fontsize=FONT_SIZE_TITLE, fontweight='bold')
        ax.set_xlabel('')
        ax.set_ylabel('Messages', fontsize=FONT_SIZE_LABEL)
        ax.legend(title='', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=FONT_SIZE_TICK)

        # Smart x-axis labels
        n_ticks = len(period_sender.index)
        if n_ticks > 20:
            step = max(1, n_ticks // 15)
            for i, label in enumerate(ax.xaxis.get_ticklabels()):
                if i % step != 0:
                    label.set_visible(False)

        plt.xticks(rotation=45, ha='right', fontsize=FONT_SIZE_TICK)
        plt.yticks(fontsize=FONT_SIZE_TICK)
        plt.tight_layout()

        return self._fig_to_bytes(fig)

    def _calculate_summary(
        self,
        df: pd.DataFrame,
        person1: Optional[str],
        person2: Optional[str],
        participants: list[dict],
    ) -> dict:
        """Calculate summary statistics."""
        total = int(len(df))
        date_min = df['datetime'].min()
        date_max = df['datetime'].max()
        days_span = int((date_max - date_min).days)

        summary = {
            "total_messages": total,
            "date_range": {
                "start": date_min.isoformat() if hasattr(date_min, 'isoformat') else str(date_min),
                "end": date_max.isoformat() if hasattr(date_max, 'isoformat') else str(date_max),
                "days": days_span,
                "years": float(round(days_span / 365, 1)),
            },
            "avg_messages_per_day": float(round(total / max(1, days_span), 1)),
            "most_active_hour": int(df['hour'].mode().iloc[0]) if not df['hour'].mode().empty else 12,
            "most_active_day": str(df['day_name'].mode().iloc[0]) if not df['day_name'].mode().empty else "Monday",
            "participants": [],
            "top_participants": [],  # For group chat summary
        }

        # Per-participant stats (for comparison mode)
        for person in [person1, person2]:
            if person:
                person_df = df[df['sender'].str.lower() == person.lower()]
                if not person_df.empty:
                    count = int(len(person_df))
                    summary["participants"].append({
                        "name": str(person),
                        "messages": count,
                        "percentage": float(round(count / total * 100, 1)),
                        "most_active_hour": int(person_df['hour'].mode().iloc[0]) if not person_df['hour'].mode().empty else 12,
                        "color": self._get_participant_color(person, participants),
                    })

        # Top participants for group chat (always include)
        top_senders = df['sender'].value_counts().head(10)
        for sender, count in top_senders.items():
            summary["top_participants"].append({
                "name": str(sender),
                "messages": int(count),
                "percentage": float(round(count / total * 100, 1)),
                "color": self._get_participant_color(str(sender), participants),
            })

        # Find longest streak
        daily = df.groupby('date').size().reset_index(name='count')
        daily['date'] = pd.to_datetime(daily['date'])
        daily = daily.sort_values('date')

        if len(daily) > 1:
            daily['day_diff'] = daily['date'].diff().dt.days
            daily['streak_break'] = daily['day_diff'] > 1
            daily['streak_id'] = daily['streak_break'].cumsum()

            streak_lengths = daily.groupby('streak_id').size()
            longest_streak = int(streak_lengths.max())
            summary["longest_streak_days"] = longest_streak

        return summary

    def _fig_to_bytes(self, fig) -> bytes:
        """Convert matplotlib figure to PNG bytes."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return buf.read()
