from pathlib import Path
from html import escape

OUT = Path('/Users/kozenki/.codex/projects/ppt_week1_final_20260909/svg_output')
NOTES = Path('/Users/kozenki/.codex/projects/ppt_week1_final_20260909/notes')
OUT.mkdir(parents=True, exist_ok=True)
NOTES.mkdir(parents=True, exist_ok=True)

W, H = 1920, 1080
BG = '#F5F9FC'
NAVY = '#083B6F'
BLUE = '#1769AA'
TEAL = '#10A9A1'
ORANGE = '#F29D38'
INK = '#17324D'
MUTED = '#62778B'
LINE = '#D8E6F0'
WHITE = '#FFFFFF'

def t(x, y, text, size=24, fill=INK, weight=400, anchor='start', cls=''):
    return f'<text x="{x}" y="{y}" font-family="STHeiti, PingFang SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="{size}px" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(str(text))}</text>'

def rect(x, y, w, h, fill=WHITE, rx=10, stroke='none', sw=0, opacity=1):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>'

def line(x1, y1, x2, y2, stroke=LINE, sw=2, dash=''):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{dash_attr}/>'

def img(href, x, y, w, h, preserve='xMidYMid meet'):
    return f'<image href="../images/{href}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="{preserve}"/>'

def base(title, kicker='WEEK 1 · 全球远程岗位数据分析'):
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080" data-pptx-page-role="slide">',
        rect(0,0,W,H,BG,0), rect(0,0,W,18,TEAL,0), rect(0,18,W,150,NAVY,0),
        rect(84,65,8,58,TEAL,4), t(120,104,title,42,WHITE,700),
        t(120,139,kicker,18,'#D6E9F6',500),
        t(1835,104,'01 / 13',16,'#CFE7F2',600,'end'),
    ]

def footer(parts, slide_no):
    parts += [line(84,1015,1836,1015,LINE,2), t(84,1045,'数据口径：仅依据《可视化分析报告》《数据预处理文档》',14,MUTED,400), t(1836,1045,f'{slide_no:02d}',14,MUTED,600,'end'), '</svg>']
    return ''.join(parts)

def save(n, content, note):
    (OUT/f'P{n:02d}.svg').write_text(content, encoding='utf-8')
    (NOTES/f'P{n:02d}.md').write_text(note, encoding='utf-8')

# 1 cover
p = ['<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080" data-pptx-page-role="slide">', rect(0,0,W,H,BG,0), rect(0,0,1920,18,TEAL,0), rect(0,18,1920,1062,NAVY,0),
     '<path d="M1180 18H1920V1060H1480C1470 820 1410 620 1280 450C1215 365 1155 240 1180 18Z" fill="#0D5B86" opacity="0.62"/>',
     '<path d="M1535 18H1920V1060H1700C1695 810 1645 610 1545 460C1495 385 1460 220 1535 18Z" fill="#0A4A78" opacity="0.7"/>',
     t(130,220,'行业大数据分析实践课程项目',20,'#9CE3DE',700),
     t(130,330,'基于全球远程招聘岗位大数据的',56,WHITE,700), t(130,405,'岗位质量评分研究',72,WHITE,700),
     t(133,487,'WEEK 1 中期汇报',28,'#BDECE8',600),
     line(130,548,830,548,'#4DBBB7',4),
     t(130,630,'学生姓名：胡善辉',22,'#D8EAF4',500), t(130,675,'班级：23大数据',22,'#D8EAF4',500),
     t(130,720,'指导教师：钟瑛',22,'#D8EAF4',500), t(130,765,'日期：2026年9月11日',22,'#D8EAF4',500),
     rect(130,880,260,52,'#0B4E75',12,'#5CD4C9',2), t(260,914,'数据 · 规则 · 模型',18,WHITE,700,'middle'), '</svg>']
save(1,''.join(p),'本页介绍项目主题、汇报范围和基本信息。')

# 2 background
p = base('研究背景与业务问题')
p += [rect(84,220,830,650,WHITE,12), rect(952,220,884,650,WHITE,12),
      t(126,278,'项目聚焦两个已完成的问题',28,NAVY,700),
      rect(126,335,720,150,'#EAF4FB',12), rect(126,522,720,150,'#E9FBF8',12),
      t(166,383,'01',30,BLUE,700), t(240,380,'岗位信息是否透明、完整？',28,INK,700),
      t(240,425,'评价招聘信息质量，帮助求职者理解信息边界。',19,MUTED,400),
      t(166,570,'02',30,TEAL,700), t(240,567,'如何把质量分复现为可学习标签？',28,INK,700),
      t(240,612,'比较四类模型，并解释模型依据。',19,MUTED,400),
      t(1004,278,'口径边界',28,NAVY,700),
      t(1004,347,'岗位质量分 ≠ 企业好坏',25,ORANGE,700),
      t(1004,405,'不代表真实工作体验',24,INK,600),
      t(1004,463,'不代表薪酬竞争力',24,INK,600),
      t(1004,521,'不代表候选人录用概率',24,INK,600),
      line(1004,575,1785,575,LINE,2),
      t(1004,628,'研究对象',18,MUTED,600), t(1004,680,'12,000 条全球远程岗位',42,BLUE,700),
      t(1004,728,'city = Remote · Himalayas 公开 Jobs API',19,MUTED,500),
      t(1004,805,'模型学习的是“信息质量代理标签”',18,TEAL,700)]
p = footer(p,2); p=p.replace('01 / 13','02 / 13'); save(2,p,'本页先把岗位质量的业务含义讲清楚，避免把信息完整度误读为企业信誉或录用概率。')

# 3 dashboard
p = base('数据范围与可追溯性')
cards=[('去重清洗岗位','12,000','全球远程岗位 · city = Remote',BLUE),('分页文件','600','每页约 20 条 · 原始响应保留',TEAL),('重复记录','0','去重后仍为 12,000 条',ORANGE),('薪资可解析','5,185','薪资缺失 6,815 条',BLUE)]
for i,(lab,val,sub,col) in enumerate(cards):
    x=84+i*432; p += [rect(x,220,408 if i<3 else 456,150,WHITE,10),rect(x,220,8,150,col,4),t(x+34,263,lab,18,INK,700),t(x+34,320,val,48,BLUE if col!=ORANGE else ORANGE,700),t(x+34,350,sub,15,MUTED,400)]
p += [rect(84,410,820,455,WHITE,12),rect(948,410,888,455,WHITE,12),t(120,456,'数据流与追溯链路',24,NAVY,700),t(120,490,'原始数据不可覆盖，结果可回到来源页核验',17,MUTED,400),
       rect(130,580,180,120,'#EAF4FB',12),rect(380,580,180,120,'#E9FBF8',12),rect(630,580,180,120,'#FFF4E6',12),
       t(220,630,'Jobs API',20,BLUE,700,'middle'),t(220,665,'公开岗位接口',16,MUTED,400,'middle'),
       t(470,630,'原始 JSONL',20,TEAL,700,'middle'),t(470,665,'600 个分页文件',16,MUTED,400,'middle'),
       t(720,630,'清洗数据',20,ORANGE,700,'middle'),t(720,665,'source_url 可回溯',16,MUTED,400,'middle'),
       line(312,640,370,640,'#8BAEC4',3),line(562,640,620,640,'#8BAEC4',3),
       t(996,456,'数据边界',24,NAVY,700),t(996,520,'时间窗口',17,MUTED,600),t(996,554,'2026.09.04 — 2026.09.08',32,BLUE,700),
       t(996,625,'保存方式',17,MUTED,600),t(996,665,'raw JSONL / API 响应保持不变',20,INK,600),t(996,707,'清洗结果写入 data/processed/',20,INK,600),t(996,749,'保留 crawl_time / data_origin',20,INK,600),t(996,791,'匹配结果可回到 source_url 核验',20,INK,600)]
p=footer(p,3).replace('01 / 13','03 / 13');save(3,p,'本页用数据看板交代样本量、文件规模、重复情况和数据追溯方式。')

# 4 cleaning
p=base('从原始岗位到可分析数据')
p += [rect(84,220,1752,640,WHITE,12), t(126,280,'清洗规范与特征工程',28,NAVY,700), t(126,316,'每一步都保留来源语义，避免把缺失值加工成业务结论。',17,MUTED,400)]
steps=[('原始 JSONL','12,000 条'),('去重','重复 0 条'),('字段标准化','类型 / 状态'),('薪资解析','币种 · 周期'),('文本清洗','HTML · URL · 空白'),('jieba 分词','中英文混合'),('技能归一化','Golang → Go'),('特征构造','长度 · 结构 · 时效')]
for i,(a,b) in enumerate(steps):
    x=126+(i%4)*410; y=385+(i//4)*205
    p += [rect(x,y,340,122,'#F2F8FC' if i%2==0 else '#EFFAF8',10),t(x+24,y+47,a,20,BLUE if i%2==0 else TEAL,700),t(x+24,y+84,b,16,MUTED,500)]
    if i%4<3: p += [line(x+340,y+61,x+390,y+61,'#A2BDCC',3)]
p += [rect(126,805,1630,46,'#FFF4E6',8),t(145,836,'保留 Python、C++、.NET 等技能符号；薪资缺失保留空值并记录解析状态。',18,'#965A1B',600)]
p=footer(p,4).replace('01 / 13','04 / 13');save(4,p,'本页展示清洗流水线：去重、类型标准化、薪资解析、文本清洗、分词、技能归一化和特征构造。')

# 5 category
p=base('岗位宽类分布')
p += [rect(84,220,1120,700,WHITE,12),rect(1240,220,596,700,WHITE,12),img('01_broad_category_distribution.png',110,255,1060,600),t(1278,286,'核心观察',22,ORANGE,700),t(1278,342,'Engineering',36,BLUE,700),t(1510,342,'2,792 条 · 23.3%',23,INK,700),t(1278,402,'Data Science',36,TEAL,700),t(1510,402,'2,199 条 · 18.3%',23,INK,700),line(1278,450,1784,450,LINE,2),t(1278,506,'业务洞察',22,ORANGE,700),t(1278,560,'样本明显偏向技术和数据岗位。',21,INK,600),t(1278,610,'后续模型与聚类建议按类别分层。',21,INK,600),t(1278,660,'求职者可先确定目标类别，再做技能匹配。',21,INK,600),rect(1278,768,470,82,'#EAF4FB',10),t(1513,804,'数据源：12,000 条去重清洗岗位',17,BLUE,700,'middle')]
p=footer(p,5).replace('01 / 13','05 / 13');save(5,p,'图表显示岗位样本偏向 Engineering 和 Data Science，因此后续分析需要注意类别结构差异。')

# 6 salary
p=base('薪资分布与职级关系')
p += [rect(84,220,820,640,WHITE,12),rect(952,220,884,640,WHITE,12),img('02_usd_salary_distribution.png',110,260,770,470),img('03_salary_by_seniority.png',978,260,830,470),
      rect(110,752,770,72,'#EAF4FB',10),t(132,783,'有效 USD 年薪样本',16,MUTED,600),t(340,786,'4,592 条',28,BLUE,700),t(540,783,'中位数 $121,550',20,INK,700),
      rect(978,752,830,72,'#FFF4E6',10),t(1000,783,'Executive 年薪中位数约',16,MUTED,600),t(1335,786,'$226,250',28,ORANGE,700),
      t(118,895,'洞察：薪资只代表主动披露 USD 的透明子样本；未披露薪资不能自动视为低薪。',18,MUTED,500)]
p=footer(p,6).replace('01 / 13','06 / 13');save(6,p,'本页强调薪资的样本边界，并用职级箱线图说明不同职级存在差异但仍有重叠。')

# 7 skills
p=base('技能与岗位描述分析')
p += [rect(84,220,1040,650,WHITE,12),rect(1160,220,676,650,WHITE,12),img('04_top_skills.png',112,255,980,520),img('05_description_length_quality.png',1200,270,590,420),
      rect(1200,730,590,90,'#E9FBF8',10),t(1220,762,'Spearman 相关',16,MUTED,600),t(1440,770,'0.67',36,TEAL,700),t(1560,762,'描述长度 ↔ 质量分',18,INK,700),
      t(1200,864,'核心观察',22,ORANGE,700),t(1200,908,'sales 出现 728 次，为最高频标签。',20,INK,600)]
p=footer(p,7).replace('01 / 13','07 / 13');save(7,p,'本页说明技能标签既包含技术词，也包含职能和角色词；描述更长通常质量更高，但长度不等于质量。')

# 8 date quality
p=base('岗位发布时间与质量等级')
p += [rect(84,220,1040,650,WHITE,12),rect(1160,220,676,650,WHITE,12),img('06_posting_date_trend.png',112,275,980,420),img('07_quality_level_distribution.png',1200,275,590,420),
      rect(120,730,940,88,'#EAF4FB',10),t(144,763,'2026.09.06 岗位数量',16,MUTED,600),t(420,773,'3,699 条',38,BLUE,700),t(620,763,'时间窗口快照，不代表完整市场趋势',18,INK,600),
      t(1200,735,'High 6,071 · 50.6%',24,BLUE,700),t(1200,780,'Medium 5,855 · 48.8%',24,TEAL,700),t(1200,825,'Low 74 · 0.6%',24,ORANGE,700),
      t(1200,885,'规则：≥80 High · 60–79 Medium · <60 Low',17,MUTED,500)]
p=footer(p,8).replace('01 / 13','08 / 13');save(8,p,'日期图是本次 API 时间窗口快照；质量等级约一半为 High，仍有大量岗位处于 Medium。')

# 9 scoring system
p=base('岗位质量如何量化')
p += [rect(84,220,1110,700,WHITE,12),rect(1228,220,608,700,WHITE,12),t(124,278,'岗位质量 = 信息透明度 + 信息完整度',28,NAVY,700),t(124,316,'总分 100，不评价企业信誉或录用概率。',17,MUTED,400)]
components=[('追溯字段',5),('核心字段',10),('地点限制',5),('描述完整性',25),('薪资透明度',15),('技能清晰度',20),('职级',10),('时效',5),('岗位类别',5)]
for i,(lab,score) in enumerate(components):
    y=375+i*52; bar=score*30
    p += [t(132,y,lab,18,INK,600),rect(355,y-19,720,28,'#EDF4F8',6),rect(355,y-19,bar,28,TEAL if score>=20 else BLUE,6),t(1110,y,f'{score} 分',18,BLUE if score<20 else TEAL,700,'end')]
p += [rect(1265,330,532,190,'#EAF4FB',12),t(1295,378,'评分依据',22,BLUE,700),t(1295,423,'source_url / crawl_time / data_origin',17,INK,600),t(1295,460,'职责 · 要求 · 福利结构',17,INK,600),t(1295,497,'薪资、技能、职级、时效、类别',17,INK,600),
       rect(1265,580,532,220,'#FFF4E6',12),t(1295,628,'解释边界',22,ORANGE,700),t(1295,673,'分数高：招聘信息更透明',20,INK,600),t(1295,716,'不等于企业更好',20,INK,600),t(1295,759,'不等于岗位一定更值得投递',20,INK,600)]
p=footer(p,9).replace('01 / 13','09 / 13');save(9,p,'本页是评分模型演示页，逐项展示 100 分由哪些信息维度构成，并强调业务边界。')

# 10 labels/model task
p=base('从规则评分到监督学习')
p += [rect(84,220,830,680,WHITE,12),rect(952,220,884,680,WHITE,12),t(126,280,'建模定义',28,NAVY,700),rect(126,335,700,135,'#EAF4FB',12),t(166,382,'quality_score ≥ 80',30,BLUE,700),t(166,430,'标记为高信息质量标签',21,INK,600),t(126,515,'模型学习的是规则生成的信息质量代理标签。',21,INK,600),t(126,572,'不是预测真实录用结果。',21,ORANGE,700),
       t(994,280,'训练 / 测试划分',28,NAVY,700),t(994,350,'总数据',17,MUTED,600),t(1240,357,'12,000',40,BLUE,700),t(994,438,'训练集',17,MUTED,600),t(1240,445,'9,600',34,TEAL,700),t(994,526,'测试集',17,MUTED,600),t(1240,533,'2,400',34,TEAL,700),t(994,614,'固定随机种子',17,MUTED,600),t(1240,620,'42',34,ORANGE,700),line(994,670,1785,670,LINE,2),t(994,730,'输入：TF-IDF、描述结构、技能数、地点、时间、经验、宽类',19,INK,600),t(994,782,'排除：quality_score、规则分项、薪资披露标记、币种、周期、标签',18,MUTED,500)]
p=footer(p,10).replace('01 / 13','10 / 13');save(10,p,'本页说明标签如何从规则生成，以及模型输入和明确排除项，重点是避免确定性泄漏。')

# 11 model results
p=base('四种模型评估结果')
p += [rect(84,220,1080,700,WHITE,12),rect(1200,220,636,700,WHITE,12),img('model_comparison.png',118,270,1010,585),t(1240,280,'测试集指标',26,NAVY,700)]
rows=[('Logistic Regression','0.8775','0.8885','0.8666','0.8774','0.9417'),('SVM','0.8729','0.8816','0.8649','0.8732','0.9381'),('Random Forest','0.8738','0.8930','0.8526','0.8723','0.9444'),('XGBoost','0.9142','0.9271','0.9012','0.9140','0.9662')]
headers=['模型','Acc','Prec','Rec','F1','AUC']
for j,h in enumerate(headers): p += [t(1240+j*95,340,h,15,MUTED,700)]
for i,row in enumerate(rows):
    y=390+i*86; fill='#E9FBF8' if i==3 else '#F7FAFC'; p += [rect(1224,y-32,572,64,fill,8)]
    for j,val in enumerate(row): p += [t(1240+j*95,y,val,15,TEAL if i==3 else INK,700 if i==3 else 500)]
p += [rect(1224,760,572,96,'#FFF4E6',10),t(1250,800,'结论',19,ORANGE,700),t(1250,835,'XGBoost 综合表现最好',23,INK,700)]
p=footer(p,11).replace('01 / 13','11 / 13');save(11,p,'本页用真实测试集指标表和模型对比图，突出 XGBoost 的 F1=0.9140、ROC-AUC=0.9662。')

# 12 explainability
p=base('模型可解释性与局限')
p += [rect(84,220,760,680,WHITE,12),rect(876,220,960,320,WHITE,12),rect(876,580,960,320,WHITE,12),img('confusion_matrices.png',110,270,710,545),img('roc_curves.png',918,260,880,270),img('feature_importance_xgboost.png',918,620,880,240),
      rect(110,838,710,46,'#EAF4FB',8),t(130,868,'混淆矩阵看分类错误；ROC 看排序区分能力。',16,BLUE,600),
      t(910,565,'解释口径',20,ORANGE,700),t(910,890,'特征重要性说明模型如何复现规则标签，不代表因果影响。',17,MUTED,500)]
p=footer(p,12).replace('01 / 13','12 / 13');save(12,p,'本页把混淆矩阵、ROC 和特征重要性放在同一页，解释模型高分的含义与局限。')

# 13 summary
p=base('项目总结与后续工作')
p += [rect(84,220,830,690,WHITE,12),rect(952,220,884,690,WHITE,12),t(126,278,'已完成',28,NAVY,700),
      t(126,338,'✓ 12,000 条全球远程岗位采集与去重',21,INK,600),t(126,392,'✓ 清洗、特征工程与 7 张业务可视化图',21,INK,600),t(126,446,'✓ 100 分岗位信息质量评分体系',21,INK,600),t(126,500,'✓ 四类模型训练、评估与可解释性分析',21,INK,600),t(126,554,'✓ 中期汇报材料与课程交付文档',21,INK,600),
      t(994,278,'下一步',28,NAVY,700),t(994,338,'• Top-k 结果进行人工相关性标注',21,INK,600),t(994,392,'• 双人标注一致性评估',21,INK,600),t(994,446,'• 句向量召回作为补充',21,INK,600),t(994,500,'• 技能词表抽样检查与岗位聚类',21,INK,600),t(994,554,'• 后续再开展 RAG / Agent / 部署',21,INK,600),
      rect(994,690,650,110,'#E9FBF8',12),t(1319,737,'谢谢聆听',34,TEAL,700,'middle'),t(1319,778,'问题讨论',22,INK,600,'middle')]
p=footer(p,13).replace('01 / 13','13 / 13');save(13,p,'最后总结已完成工作与后续计划，明确 RAG、Agent 和部署仍属于后续工作。')

print(f'Wrote {len(list(OUT.glob("P*.svg")))} SVG pages to {OUT}')
