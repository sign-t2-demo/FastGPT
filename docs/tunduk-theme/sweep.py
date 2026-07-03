#!/usr/bin/env python3
"""Tunduk 主题色值清扫：把旧 token 色值按映射表替换为设计确认的新值。
范围：packages/{web,global,service} + projects/app 下的 .ts/.tsx/.scss/.css
（node_modules/.next/dist/coverage 排除）。hex 匹配大小写不敏感，输出统一大写。
rgba 数字三元组只在 rgb(/rgba( 前缀内替换。

用法：
  python3 sweep.py          # 代码文件（ts/tsx/scss/css）
  python3 sweep.py --svg    # 仅 SVG 素材；自动跳过品牌素材（BRAND_EXCLUDE）
  加 --dry 只报告不写入
"""
import os, re, sys
from collections import defaultdict

# 品牌素材：等设计师提供 Tunduk 版本，不做机械换色
BRAND_EXCLUDE = {'logo.svg', 'botTextCN.svg', 'botTextEn.svg'}

# 仓库根目录 = 本脚本(docs/tunduk-theme/sweep.py)向上两级，不依赖运行时 cwd
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCOPES = ['packages/web', 'packages/global', 'packages/service', 'projects/app']
SVG_MODE = '--svg' in sys.argv
DRY_RUN = '--dry' in sys.argv
EXTS = {'.svg'} if SVG_MODE else {'.ts', '.tsx', '.scss', '.css'}
EXCLUDE_DIRS = {'node_modules', '.next', 'dist', 'coverage', 'build', '.turbo'}

HEX_MAP = {
    # primary / blue (旧蓝 → 新红)
    '3370FF': 'C8102E', '487FFF': 'D6203A', '2B5FD9': 'A50C22',
    '2450B5': '83091B', '1D4091': '660714', '5E8FFF': 'DF4F64',
    '94B5FF': 'E97F8D', 'C5D7FF': 'F2ACB5', 'E1EAFF': 'F8D3D8', 'F0F4FF': 'FCE9EB',
    # lgColor 渐变
    '2152D9': 'A50C22', '4E83FD': 'D6203A', '85B1FF': 'E8556B',
    'D6E8FF': 'F7D3D8', 'F0F7FF': 'FCF0F1',
    # myGray 冷灰 → 暖灰（FBFBFC 有歧义，theme.ts 内 myGray.25 已单独处理，其余按 myWhite.300 映射）
    '111824': '1F1A17', '1D2532': '28221D', '383F50': '322B26', '485264': '3A332E',
    '667085': '7A6F63', '8A95A7': 'A89C8C', 'C4CBD7': 'CBBFAC', 'DFE2EA': 'EADFCE',
    'E8EBF0': 'ECE3D6', 'F0F1F6': 'F1EAE0', 'F4F4F7': 'F2ECE2', 'F7F8FA': 'F4EFE7',
    'FBFBFC': 'FBF8F3',
    # borders md/lg 遗留绿灰
    'DAE0E2': 'E5D8C6', 'D0E0E2': 'DCCEB9',
    # myWhite
    'FEFEFE': 'FEFDFC', 'FDFDFE': 'FDFBF8', 'F8FAFB': 'F9F5EE', 'F6F8F9': 'F8F3EA',
    'F4F6F8': 'F6F1E7', 'C3C5C6': 'C8C1B5', '929495': '979086',
    '626263': '655F56', '313132': '332E29',
    # green
    '12B76A': '2F9155', '039855': '217A45', '027A48': '1B6338',
    '05603A': '15502D', '054F31': '104123',
    # yellow → gold
    'FEDF89': 'FBE28A', 'F5C149': 'F5C518', 'FDB022': 'E7B40D', 'F79009': 'D9A400',
    'DC6803': 'B58800', 'B54708': '8F6B00', '93370D': '6F5300', '7A2E0E': '5A4300',
}
# rgba/rgb 内的数字三元组映射
TRIPLE_MAP = [
    (r'(rgba?\(\s*)51\s*,\s*112\s*,\s*255', r'\g<1>200, 16, 46'),    # primary
    (r'(rgba?\(\s*)19\s*,\s*51\s*,\s*107', r'\g<1>74, 58, 40'),      # 阴影海军蓝 → 暖棕
    (r'(rgba?\(\s*)17\s*,\s*24\s*,\s*36', r'\g<1>31, 26, 23'),        # myGray alpha
]

hex_patterns = {old: re.compile('#' + ''.join('[%s%s]' % (c.lower(), c.upper()) if c.isalpha() else c for c in old))
                for old in HEX_MAP}

stats = defaultdict(lambda: defaultdict(int))
changed_files = []
for scope in SCOPES:
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, scope)):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1] not in EXTS:
                continue
            if SVG_MODE and fn in BRAND_EXCLUDE:
                stats['(skipped brand asset) ' + os.path.join(dirpath, fn)]['skipped'] += 1
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding='utf-8') as f:
                    src = f.read()
            except UnicodeDecodeError:
                # 非 UTF-8（可能是伪装扩展名的二进制），跳过并报告，人工检查
                stats['(skipped non-utf8) ' + path]['skipped'] += 1
                continue
            out = src
            for old, pat in hex_patterns.items():
                out, n = pat.subn('#' + HEX_MAP[old], out)
                if n:
                    stats[path]['#' + old] += n
            for pat, repl in TRIPLE_MAP:
                out, n = re.subn(pat, repl, out)
                if n:
                    stats[path][pat[:24]] += n
            if out != src:
                if not DRY_RUN:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(out)
                changed_files.append(path)

print(f"changed files{' (dry-run)' if DRY_RUN else ''}: {len(changed_files)}")
for path in sorted(changed_files):
    rel = os.path.relpath(path, ROOT)
    detail = ', '.join(f'{k}×{v}' for k, v in sorted(stats[path].items()))
    print(f'  {rel}: {detail}')
skipped = [p for p in stats if p.startswith('(skipped')]
for p in sorted(skipped):
    print(' ', p)
