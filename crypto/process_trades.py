#!/usr/bin/env python3
# coding = utf-8
"""
读取 crypto 目录下的成交记录 Excel（如：匯出歷史成交-YYYY-MM-DD hh_mm_ss.xlsx），
按【到秒 + 交易链路(pair) + 交易类型(type)】归并，输出到 crypto-invest-log.xlsx：
- 第一个sheet为汇总（按年-月聚合，并生成按月图表）
- 其余sheet按交易年份划分

注意：--start/--end 参数用于“筛选交易时间字段（列 date/交易时间）”，
      不用于控制或匹配源文件名。源文件会基于固定通配符从 crypto 目录自动发现并读取。

用法：
  交互模式：直接运行后根据提示输入起止日期（YYYY-MM-DD），可回车跳过使用全部数据范围
  命令行：python crypto/process_trades.py --start 2024-01-01 --end 2024-12-31
"""

import os
import sys
import glob
import argparse
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd


SOURCE_GLOB_PATTERNS = [
    '匯出歷史成交-*.xlsx',  # 繁体/中文命名
    '汇出历史成交-*.xlsx',   # 简体命名（以防万一）
]


COLUMN_MAP = {
    '交易时间': 'date',
    'date(utc)': 'date',
    'date (utc)': 'date',
    '交易链路': 'pair',
    '交易类型': 'type',
    '成交价格': 'price',
    '成交量': 'amount',
    '成交金额': 'total',
    '买入币种': 'base_asset',
    'base asset': 'base_asset',
    'base_asset': 'base_asset',
    # 兼容英文/其他导出（统一为小写键做匹配）
    'date': 'date',
    'pair': 'pair',
    'type': 'type',
    'price': 'price',
    'amount': 'amount',
    'total': 'total',
}

def _normalize_col_key(col: str) -> str:
    # 去除首尾空格，合并内部多余空格，并小写
    # 同时将全角/半角括号统一为半角
    if col is None:
        return ''
    s = str(col).strip().replace('（', '(').replace('）', ')')
    s = ' '.join(s.split())
    return s.lower()


def find_source_files(directory: str) -> List[str]:
    files: List[str] = []
    for pat in SOURCE_GLOB_PATTERNS:
        files.extend(glob.glob(os.path.join(directory, pat)))
    # 去重并排序（按修改时间）
    files = sorted(set(files), key=lambda p: os.path.getmtime(p))
    return files


def read_and_concat(files: List[str]) -> pd.DataFrame:
    frames = []
    for f in files:
        df = pd.read_excel(f, engine='openpyxl')
        # 统一列名（大小写/空白不敏感）
        col_map_lower = { _normalize_col_key(k): v for k, v in COLUMN_MAP.items() }
        rename_map = {}
        for c in df.columns:
            key = _normalize_col_key(c)
            rename_map[c] = col_map_lower.get(key, c)
        df = df.rename(columns=rename_map)
        # 仅保留需要字段（包含 base_asset，模板必然提供）
        keep_cols = ['date', 'pair', 'type', 'price', 'amount', 'total', 'base_asset']
        missing = [c for c in keep_cols if c not in df.columns]
        if missing:
            raise ValueError(f"文件 {os.path.basename(f)} 缺少必要字段: {missing}")
        frames.append(df[keep_cols].copy())
    if not frames:
        return pd.DataFrame(columns=['date', 'pair', 'type', 'price', 'amount', 'total'])
    return pd.concat(frames, ignore_index=True)


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    # 日期解析（源为UTC），统一转换为北京时间（Asia/Shanghai, UTC+8）并去除时区标记
    df['date'] = pd.to_datetime(df['date'], errors='coerce', utc=True)
    df['date'] = df['date'].dt.tz_convert('Asia/Shanghai').dt.tz_localize(None)
    # 数值转换
    for col in ['price', 'amount', 'total']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    # 丢弃无效行
    df = df.dropna(subset=['date', 'pair', 'type', 'price', 'amount', 'total'])
    # 规范字符串
    df['pair'] = df['pair'].astype(str).str.strip()
    df['type'] = df['type'].astype(str).str.strip().str.lower()
    return df


def prompt_date(prompt_msg: str) -> Optional[datetime]:
    raw = input(prompt_msg).strip()
    if not raw:
        return None
    return datetime.strptime(raw, '%Y-%m-%d')


def parse_args() -> Tuple[Optional[datetime], Optional[datetime], bool]:
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=str, help='起始日期，格式 YYYY-MM-DD')
    parser.add_argument('--end', type=str, help='结束日期，格式 YYYY-MM-DD')
    parser.add_argument(
        '--dedupe',
        type=str,
        choices=['on', 'off'],
        default='on',
        help='是否在聚合前按关键字段去重（默认 on）'
    )
    args, _ = parser.parse_known_args()

    start_dt = datetime.strptime(args.start, '%Y-%m-%d') if args.start else None
    end_dt = datetime.strptime(args.end, '%Y-%m-%d') if args.end else None
    dedupe_enabled = (args.dedupe == 'on')

    if start_dt is None and end_dt is None and sys.stdin.isatty():
        print('请输入需要处理订单的起止日期，直接回车表示不限制：')
        start_dt = prompt_date('起始日期(YYYY-MM-DD): ')
        end_dt = prompt_date('结束日期(YYYY-MM-DD): ')
    return start_dt, end_dt, dedupe_enabled


def dedupe_orders(df: pd.DataFrame, enabled: bool) -> pd.DataFrame:
    if not enabled or df.empty:
        return df
    before = len(df)
    # 基于完整关键字段集合进行精确行去重
    key_cols = ['date', 'pair', 'type', 'base_asset', 'price', 'amount', 'total']
    # 只保留这些列都存在的情况（正常应已满足）
    existing = [c for c in key_cols if c in df.columns]
    if len(existing) < len(key_cols):
        # 若有缺失，保守返回不去重
        return df
    df = df.sort_values(existing).drop_duplicates(subset=existing, keep='first').reset_index(drop=True)
    after = len(df)
    removed = before - after
    if removed > 0:
        print(f'去重已启用：移除重复行 {removed} 条（{before} -> {after}）。')
    else:
        print('去重已启用：未发现重复行。')
    return df


def filter_by_date(df: pd.DataFrame, start_dt: Optional[datetime], end_dt: Optional[datetime]) -> pd.DataFrame:
    if start_dt is not None:
        df = df[df['date'] >= pd.Timestamp(start_dt)]
    if end_dt is not None:
        # 包含当天，截止到 23:59:59
        end_inclusive = pd.Timestamp(end_dt) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df = df[df['date'] <= end_inclusive]
    return df


def aggregate_orders(df: pd.DataFrame) -> pd.DataFrame:
    # 到秒
    df['date_second'] = df['date'].dt.floor('s')
    grouped = df.groupby(['date_second', 'pair', 'type', 'base_asset'], as_index=False).agg(
        amount_sum=('amount', 'sum'),
        total_sum=('total', 'sum')
    )
    # 加权价格
    grouped['price'] = grouped.apply(
        lambda r: (r['total_sum'] / r['amount_sum']) if r['amount_sum'] else 0.0, axis=1
    )
    grouped = grouped.rename(columns={
        'date_second': 'date',
        'amount_sum': 'amount',
        'total_sum': 'total',
    })
    # 排序
    grouped = grouped.sort_values(by=['date', 'pair', 'type']).reset_index(drop=True)
    return grouped[['date', 'pair', 'type', 'base_asset', 'price', 'amount', 'total']]


def build_summary(agg_df: pd.DataFrame) -> pd.DataFrame:
    df = agg_df.copy()
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month

    # 分 buy/sell 统计与净额
    pivot = df.pivot_table(
        index=['year', 'month'],
        columns='type',
        values=['amount', 'total'],
        aggfunc='sum',
        fill_value=0.0,
        observed=True,
    )
    # 扁平列名 amount_buy, total_buy, ...
    pivot.columns = [f"{a}_{b}" for a, b in pivot.columns]
    pivot = pivot.reset_index()

    # 计算净买入金额（以 total 计）
    buy_total_col = 'total_buy' if 'total_buy' in pivot.columns else None
    sell_total_col = 'total_sell' if 'total_sell' in pivot.columns else None
    pivot['net_total'] = 0.0
    if buy_total_col:
        pivot['net_total'] += pivot[buy_total_col]
    if sell_total_col:
        pivot['net_total'] -= pivot[sell_total_col]

    return pivot.sort_values(['year', 'month']).reset_index(drop=True)


def write_excel(agg_df: pd.DataFrame, out_path: str) -> None:
    if agg_df.empty:
        # 也写一个空模板
        with pd.ExcelWriter(out_path, engine='xlsxwriter') as writer:
            empty = pd.DataFrame(columns=['date', 'pair', 'type', 'price', 'amount', 'total'])
            empty.to_excel(writer, sheet_name='summary', index=False)
        return

    summary_df = build_summary(agg_df)

    with pd.ExcelWriter(out_path, engine='xlsxwriter', datetime_format='yyyy-mm-dd hh:mm:ss') as writer:
        # 1) 写入汇总 sheet
        summary_df.to_excel(writer, sheet_name='summary', index=False)

        # 添加图表：按年-月的净买入金额
        workbook  = writer.book
        worksheet = writer.sheets['summary']
        chart = workbook.add_chart({'type': 'column'})

        # 找到每年数据区间，创建多序列（每个年份一条序列，X轴为月份）
        years = sorted(summary_df['year'].unique())
        start_row = 1  # 数据起始行（0是表头）
        for y in years:
            year_rows = summary_df[summary_df['year'] == y]
            if year_rows.empty:
                continue
            first_idx = year_rows.index.min()
            last_idx  = year_rows.index.max()
            # 列索引：A(year)=0, B(month)=1, ... 找到 net_total 列位置
            net_col = summary_df.columns.get_loc('net_total')
            month_col = summary_df.columns.get_loc('month')

            chart.add_series({
                'name':       [ 'summary',  first_idx + start_row, 0 ],  # 用该行年份单元格作为名称
                'categories': [ 'summary',  first_idx + start_row, month_col, last_idx + start_row, month_col ],
                'values':     [ 'summary',  first_idx + start_row, net_col,   last_idx + start_row, net_col ],
            })

        chart.set_title({'name': '按月净买入金额（分年对比）'})
        chart.set_x_axis({'name': '月份'})
        chart.set_y_axis({'name': '金额'})
        chart.set_style(10)
        worksheet.insert_chart('J2', chart, {'x_scale': 1.4, 'y_scale': 1.4})

        # 2) 各年份明细 sheet
        agg_df['year'] = agg_df['date'].dt.year
        for year, df_year in agg_df.groupby('year'):
            out_cols = ['date', 'pair', 'type', 'base_asset', 'price', 'amount', 'total']
            df_out = df_year[out_cols].copy().sort_values('date')
            sheet_name = str(year)
            df_out.to_excel(writer, sheet_name=sheet_name, index=False)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    files = find_source_files(here)
    if not files:
        print('未在 crypto 目录下找到成交记录文件（匯出歷史成交-*.xlsx），请先放置文件后再运行。')
        sys.exit(1)

    start_dt, end_dt, dedupe_enabled = parse_args()
    raw_df = read_and_concat(files)
    raw_df = coerce_types(raw_df)
    raw_df = filter_by_date(raw_df, start_dt, end_dt)
    raw_df = dedupe_orders(raw_df, dedupe_enabled)

    if raw_df.empty:
        print('筛选后无数据，退出。')
        sys.exit(0)

    agg_df = aggregate_orders(raw_df)

    out_path = os.path.join(here, 'crypto-invest-log.xlsx')
    write_excel(agg_df, out_path)
    print(f'已生成: {out_path}')


if __name__ == '__main__':
    main()


