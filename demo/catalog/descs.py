# -*- coding: utf-8 -*-
"""数据总目 · 语义层：中文说明（三档信度）+ 家族归类 + 关系推断
信度: ok=实证(本会话亲验)  doc=通说(公开文档/名称自明)  guess=推断(仅凭名称,页面标?)
"""

# ---------- public 86 表（CBDB 人物库） ----------
PUB = {
 'biog_main': ('人物主表：姓名·性别·朝代·索引年·生卒·籍贯指针·模糊年代编码·整理注记', 'ok'),
 'biog_source_data': ('人物↔传记出处桥（全库最大表：每人每条文献引用一行，含页码）', 'ok'),
 'posted_to_office_data': ('除授记录主表（人×官职×起讫年×除授方式）', 'doc'),
 'posting_data': ('除授事件表（与 posted_to_office_data 按 c_posting_id 成对）', 'doc'),
 'kin_data': ('亲属关系有向记录（A 之父/妻/子为 B；56.3 万条）', 'ok'),
 'posted_to_addr_data': ('除授→任地桥（c_posting_id→c_addr_id）', 'ok'),
 'biog_addr_data': ('人物↔地址（22 类：籍贯/户籍/寓居/死所/葬地…46 万条）', 'ok'),
 'entry_data': ('入仕记录（科举/荐举/荫补；年份以纪年 c_entry_nh_year 存）', 'ok'),
 'altname_data': ('别名记录（字/号/谥/封号/法名…21 类）', 'doc'),
 'assoc_data': ('社会交往记录（人×人×498 类关系×年×地×文本证据）', 'ok'),
 'status_data': ('人物身份记录（平民/军户/儒户/官户…）', 'doc'),
 'text_codes': ('文献主表（书名/作者/存佚/类型；6.2 万种）', 'doc'),
 'biog_text_data': ('人物↔文本著作关系（著/编/注/序）', 'doc'),
 'office_code_type_rel': ('官职↔官职类型 多对多桥', 'doc'),
 'quan_yuan_wen_index': ('《全元文》篇目索引（专藏整合数据）', 'doc'),
 'addr_belongs_data': ('地名隶属关系（县↔州↔路，带起讫年）', 'doc'),
 'office_codes': ('官职名受控词表（中英双语，3.4 万职名）', 'ok'),
 'addr_codes': ('历史地名主表（30,157 名，15,555 带经纬度）', 'ok'),
 'addr_xy': ('地名坐标辅助表（坐标装配中间层）', 'guess'),
 'text_instance_data': ('文本实例（版本/藏本）记录', 'guess'),
 'spatial_ref_sys': ('PostGIS 系统表：SRID 坐标系定义（8,501 种）', 'ok'),
 'merged_person_data': ('人物合并记录（重目归并：旧 id→新 id）', 'doc'),
 'social_institution_codes': ('社会机构词表（学校/书院/寺观/衙署…）', 'doc'),
 'social_institution_addr': ('社会机构↔地址', 'doc'),
 'gb_91_codes': ('国标代码表（≈县级政区码）', 'guess'),
 'academies_2957': ('历代书院 2,957 处（带坐标；Demo E 用）', 'ok'),
 'office_type_tree': ('官职类型层级树', 'doc'),
 'social_institution_name_codes': ('机构名称词表', 'doc'),
 'china_pop_1999_county': ('1999 年全国县级人口数据', 'doc'),
 'missionary_writings': ('来华传教士著述专表', 'doc'),
 'nian_hao': ('年号主表（年号↔朝代↔起讫年；682 条）', 'doc'),
 'biog_inst_data': ('人物↔机构关系', 'doc'),
 'assoc_codes': ('社会关系类型词表（498 类）', 'ok'),
 'ethnicity_tribe_codes': ('族群/部族词表', 'doc'),
 'kinship_codes': ('亲属类型词表（488 类）', 'ok'),
 'assoc_code_type_rel': ('社会关系↔大类 多对多桥', 'doc'),
 'events_data': ('历史事件记录（军事/政治/礼仪…）', 'doc'),
 'status_code_type_rel': ('身份↔大类 多对多桥', 'doc'),
 'status_codes': ('社会身份词表', 'doc'),
 'entry_code_type_rel': ('入仕↔大类 多对多桥', 'doc'),
 'entry_codes': ('入仕途径词表（273 类）', 'ok'),
 'admin_cat_codes': ('政区类别词表', 'doc'),
 'choronym_codes': ('郡望（choronym）词表', 'doc'),
 'thdl_tibet_adm_areas': ('THDL 西藏行政区划（藏学与喜马拉雅数字图书馆）', 'doc'),
 'kin_mourning_steps': ('服制等级定义（斩衰/齐衰/大功/小功/缌麻五服）', 'doc'),
 'kin_mourning': ('亲属关系↔丧服服制映射', 'doc'),
 'text_biblcat_code_type_rel': ('文献分类↔类型桥', 'doc'),
 'text_biblcat_codes': ('文献分类词表（四部/细分）', 'doc'),
 'text_type': ('文本类型词表（诗/文/书启/碑志…）', 'doc'),
 'event_codes': ('事件类型词表', 'doc'),
 'appointment_codes': ('除授方式词表（除/拜/迁/罢…）', 'doc'),
 'appointment_code_type_rel': ('除授方式↔大类桥', 'doc'),
 'dynasties': ('朝代主表（代码↔中英名↔起讫；85 行含辽金西夏等政权）', 'ok'),
 'possession_addr': ('拥有物（庄产等）↔地址桥', 'guess'),
 'ganzhi_codes': ('六十干支词表', 'ok'),
 'possession_data': ('人物拥有物记录（庄产/资产）', 'guess'),
 'text_biblcat_types': ('文献分类大类表', 'doc'),
 'assoc_types': ('社会关系大类表（45 大类统 498 类）', 'doc'),
 'household_status_codes': ('户状态词表（民/军/匠/灶…）', 'doc'),
 'scholarlytopic_codes': ('学术主题词表（理学/考据…）', 'doc'),
 'indexyear_type_codes': ('索引年类型词表（生/卒/及第/任官…31 类）', 'ok'),
 'entry_types': ('入仕途径大类表', 'doc'),
 'biog_inst_codes': ('人物↔机构关系类型词表', 'doc'),
 'biog_addr_codes': ('地址类型词表（22 类）', 'ok'),
 'altname_codes': ('别名类型词表（21 类）', 'ok'),
 'office_categories': ('官职大类表', 'doc'),
 'status_types': ('身份大类表', 'doc'),
 'appointment_types': ('除授大类表', 'doc'),
 'literarygenre_codes': ('文学体裁词表（寿序/挽词…用于交往记录）', 'doc'),
 'text_role_codes': ('文本角色词表（作者/编者/注者/序者）', 'doc'),
 'country_codes': ('现代国家代码表', 'guess'),
 'occasion_codes': ('交往场合词表（生辰/饯别/哀挽…）', 'doc'),
 'kinrel_reduction': ('亲属关系归约规则（复合关系化简）', 'guess'),
 'measure_codes': ('计量单位词表', 'guess'),
 'parental_status_codes': ('父母存殁状态词表（具庆/永感…）', 'guess'),
 'social_institution_types': ('机构大类表', 'doc'),
 'assume_office_codes': ('到任方式代码', 'guess'),
 'year_range_codes': ('年代区间词表（「X 与 Y 之间」的模糊编码）', 'ok'),
 'events_addr': ('事件↔地址桥', 'doc'),
 'extant_codes': ('文本存佚词表（存/佚/未见）', 'doc'),
 'possession_act_codes': ('拥有行为词表', 'guess'),
 'social_institution_addr_types': ('机构地址类型词表', 'doc'),
 'social_institution_altname_codes': ('机构别名类型词表', 'doc'),
 'admin_cat_code_type_rel': ('政区类别↔类型桥（空表）', 'doc'),
 'admin_cat_types': ('政区类别大类（空表）', 'doc'),
 'social_institution_altname_data': ('机构别名记录（空表）', 'doc'),
 'geography_columns': ('PostGIS 系统视图：地理列注册', 'ok'),
 'geometry_columns': ('PostGIS 系统视图：几何列注册（查全库空间表入口）', 'ok'),
 'raster_columns': ('PostGIS 系统视图：栅格列注册', 'ok'),
 'raster_overviews': ('PostGIS 系统视图：栅格概览层', 'ok'),
}

# ---------- chgis 显式 ----------
CHGIS = {
 'dem': ('~1km 高程栅格瓦片（3,358 片；Demo E 庐山地形数据源）', 'ok'),
 'dem_gtopo30': ('GTOPO30 全球高程栅格', 'doc'),
 'china_chron': ('中国年代学总表（朝代/时期/年号/庙号↔起讫↔对照译名）', 'doc'),
 'china_chron_fields': ('china_chron 字段说明表', 'doc'),
 'major_china_periods': ('中国主要历史时期表', 'doc'),
 'gazetteers_beta': ('地名辞典 beta（工作层）', 'guess'),
 'chinaw_master_beta': ('ChinaW 地名主表 beta', 'guess'),
 'manshu_200k_index': ('满洲 1:20 万地形图图幅索引', 'guess'),
 'chgis_tmpl_28apr': ('CHGIS 模板表（4月28日工作稿）', 'guess'),
 'minggarrisonssheet_29jan08': ('明代卫所工作稿（2008-01-29）', 'guess'),
 'ming_garrisons': ('明代卫所驻军点', 'doc'),
 'ming_routes_2016': ('明代驿路（线）', 'doc'),
 'ming_stations_2016': ('明代驿站 1,000 处（点）', 'doc'),
 'hartwell_pref_pgn': ('Hartwell 府级面·四朝代快照 741/1080/1200/1391（Demo A 底图）', 'ok'),
 'hartwell_cnty_pgn': ('Hartwell 县级面 8,146（县级分辨率升级用）', 'ok'),
 'hartwell_circ_pgn': ('Hartwell 路/道级面', 'doc'),
 'hartwell_prov_pgn': ('Hartwell 省级面', 'doc'),
 'hartwell_chin_pgn': ('Hartwell 各朝代疆域总轮廓（面）', 'guess'),
 'hartwell_chin_pts': ('Hartwell 各朝代疆域总轮廓（点）', 'guess'),
 'hartwell_indp_pgn': ('Hartwell 独立政权面（割据诸国）', 'guess'),
 'hartwell_jin_pgn': ('Hartwell 金代政区面', 'doc'),
 'hartwell_liao_pgn': ('Hartwell 辽代政区面', 'doc'),
 'v6_pref_pgn': ('CHGIS V6 时序府级面（beg/end 生效年；宋代缺面，见 Demo A 校勘台）', 'ok'),
 'v6_pref_pts': ('CHGIS V6 时序府级点（1100 年生效 355）', 'ok'),
 'v6_cnty_pts': ('CHGIS V6 时序县级点（1100 年生效 1,252）', 'ok'),
 'v3_dem_topo30': ('V3 GTOPO30 高程层', 'doc'),
 'v5_smr_pgn': ('施坚雅（G.W.Skinner）生理大区面', 'doc'),
 'v5_smr_subr_pgn': ('施坚雅大区下属亚区面', 'doc'),
 'v5_physiog_macroregions': ('生理大区面（GBK 名）', 'doc'),
 'v5_physiog_macroregions_utf': ('生理大区面（UTF 名）', 'doc'),
 'v5_2009_tibet_twns': ('2009 西藏乡镇点', 'doc'),
 'v5_chinaw_pts': ('ChinaW 地名点（V5 整合）', 'guess'),
 'v4_gns': ('GNS 美国国家地理空间情报署地名（V4 整合）', 'doc'),
 'v5_gns': ('GNS 地名（V5 整合）', 'doc'),
 'v4_buddhist_pts': ('佛教寺观点位（V4 整合）', 'doc'),
 'v2_beijing_sites_pgn': ('北京历史遗址面（V2 整合）', 'doc'),
 'v4_data_dictionary': ('V4 数据字典', 'doc'),
 'v4_feature_types': ('V4 要素类型表', 'doc'),
 'xtra_change_types': ('变更类型表（跨版本工作层）', 'doc'),
 'xtra_contributors': ('贡献者表（跨版本工作层）', 'doc'),
 'xtra_date_rules': ('日期规则表（起讫年解释规约）', 'doc'),
 'xtra_geo_source': ('地理来源表（跨版本工作层）', 'doc'),
}
# V 系规则词根
_VER = {'v2':'V2','v3':'V3','v4':'V4','v5':'V5','v6':'V6'}
_SNAP = {'1820':'1820（嘉庆25）基准','1911':'1911（宣统3）基准','1997':'1997 基准','1926':'1926 基准','1990':'1990 基准'}
_FEAT = {'cnty':'县级','pref':'府级','prov':'省级','reg':'大区','twn':'乡镇聚落点','cst':'海岸线','coast':'海岸线',
         'rvr':'河流','coded_rvr':'河流（带编码）','lks':'湖泊','rds':'道路','rail':'铁路','contour':'等高线',
         'mtns':'山峰点','rocks':'岩礁点','citas_cnty':'CITAS 县级','citas_pref':'CITAS 府级'}
_GEOMT = {'pgn':'面','pts':'点','lin':'线','pgn_big5_stats':'面（Big5 统计）','pgn_gbk_stats':'面（GBK 统计）','pgn_utf_stats':'面（UTF 统计）'}
_DBINNER = {'main_table':'主表','main':'主表','partof_table':'隶属关系','part_of':'隶属关系','partof':'隶属关系',
            'source_notes_table':'来源注记','source_notes':'来源注记','gisinfo_table':'GIS 元数据','gis_info':'GIS 元数据',
            'data_dictionary':'数据字典','feature_types':'要素类型','other_feature_types':'其他要素类型',
            'contrib_table':'贡献者','contributors':'贡献者','date_rule_table':'日期规则','date_rules':'日期规则',
            'geo_source':'地理来源','change_type':'变更类型','change_types':'变更类型','preceded_by_table':'沿革前身关系',
            'preceded_by':'沿革前身关系','gis_layer_field_names':'图层字段名','gis_layer_field':'图层字段名'}

def chgis_desc(tb):
    if tb in CHGIS: return CHGIS[tb]
    p = tb.split('_')
    # vXdb_yy_* 发行版内部表
    if p[0] in ('v2db','v3db','v4db','v5db','v6db'):
        ver = _VER[p[0][:2]]
        inner = '_'.join(p[1:])
        for k, v in _DBINNER.items():
            if inner.startswith(k):
                inner = inner[len(k):].strip('_')
                return (f'{ver} 发行库 · {v}' + ('（'+inner+'）' if inner else ''), 'doc')
        return (f'{ver} 发行库内部表（{inner}）', 'guess')
    # v4_ras_* / russ 系
    if len(p) > 2 and p[0].startswith('v') and p[1] == 'ras':
        return (f'{_VER.get(p[0],p[0])} × 俄国勘探图点位（{"_".join(p[2:])}）', 'guess')
    # vX_(snapshot|time|dcw|dem|citas90|nima)_feat_geom
    if p[0] in _VER:
        ver = _VER[p[0]]; rest = p[1:]
        if rest and rest[0] == 'time':
            f = _FEAT.get(rest[1], rest[1]) if len(rest) > 1 else ''
            g = _GEOMT.get(rest[2], rest[2]) if len(rest) > 2 else ''
            return (f'{ver} 时序层 · {f}{g}（beg_yr/end_yr 生效区间）', 'doc')
        if rest and rest[0] == 'dem':
            return (f'{ver} DEM 高程层（{"_".join(rest[1:])}）', 'doc')
        if rest and rest[0] == 'dcw':
            f = _FEAT.get('_'.join(rest[1:]), '_'.join(rest[1:]))
            return (f'{ver} × DCW 底图 · {f}', 'doc')
        if rest and rest[0] == 'nima':
            f = _FEAT.get(rest[1], rest[1]) if len(rest) > 1 else ''
            g = _GEOMT.get(rest[2], rest[2]) if len(rest) > 2 else ''
            return (f'{ver} × NIMA 地名 · {f}{g}', 'doc')
        if rest and rest[0] == 'citas90':
            f = _FEAT.get(rest[1], rest[1]) if len(rest) > 1 else ''
            g = '_'.join(rest[2:])
            return (f'{ver} × CITAS 1990 · {f}{g}', 'doc')
        if rest and rest[0] in _SNAP:
            f = _FEAT.get(rest[1], rest[1]) if len(rest) > 1 else ''
            g = _GEOMT.get(rest[2], rest[2]) if len(rest) > 2 else ''
            return (f'{ver} · {_SNAP[rest[0]]} · {f}{g}', 'doc')
    return ('', 'guess')

# ---------- harv ----------
HARV = {
 'tgaz_placename': ('TGaz 地名主表（82,117 地名）', 'ok'),
 'tgaz_spelling': ('TGaz 历史拼写/异体记录（245,042 条）', 'ok'),
 'tgaz_part_of': ('TGaz 地名隶属关系（83,400 条）', 'ok'),
 'tgaz_partof_xx': ('TGaz 隶属关系（扩展版）', 'guess'),
 'tgaz_present_loc': ('TGaz 今地对应', 'doc'),
 'tgaz_v6_id': ('TGaz↔CHGIS V6 ID 桥', 'doc'),
 'tgaz_v5_id': ('TGaz↔CHGIS V5 ID 桥', 'doc'),
 'tgaz_snote': ('TGaz 来源注记', 'doc'),
 'tgaz_snote_xx': ('TGaz 来源注记（扩展版）', 'guess'),
 'tgaz_alt_name3': ('TGaz 别名', 'doc'),
 'tgaz_admin_seat': ('TGaz 治所记录', 'doc'),
 'tgaz_citation_ref': ('TGaz 引用文献参照', 'doc'),
 'tgaz_data_src': ('TGaz 数据源清单', 'doc'),
 'tgaz_drule': ('TGaz 日期规则', 'guess'),
 'tgaz_f2': ('TGaz 内部表 f2', 'guess'),
 'tgaz_ftype': ('TGaz 要素类型', 'doc'),
 'tgaz_ftype_xx': ('TGaz 要素类型（扩展版）', 'guess'),
 'tgaz_geom': ('TGaz 几何表', 'doc'),
 'tgaz_gis_xx': ('TGaz GIS 元数据（扩展版）', 'guess'),
 'tgaz_link': ('TGaz 关联链接', 'guess'),
 'tgaz_main_xx': ('TGaz 主表（扩展版）', 'guess'),
 'tgaz_mv_pn_srch': ('TGaz 地名检索物化视图', 'doc'),
 'tgaz_mv_pn_srch_old': ('TGaz 地名检索物化视图（旧版）', 'guess'),
 'tgaz_mv_pn_srch_new_test': ('TGaz 地名检索物化视图（新版测试）', 'guess'),
 'tgaz_prec_by': ('TGaz 沿革前身', 'guess'),
 'tgaz_precby_xx': ('TGaz 沿革前身（扩展版）', 'guess'),
 'tgaz_script': ('TGaz 文字系统（汉字/蒙文/满文/藏文…）', 'guess'),
 'tgaz_spatial_system_ref': ('TGaz 空间参考系定义', 'doc'),
 'tgaz_tbt_rev': ('TGaz 待复核记录（id/name_id/x/y）', 'guess'),
 'tgaz_temporal_annotation': ('TGaz 时间标注', 'doc'),
 'tgaz_trsys': ('TGaz 转写系统', 'guess'),
 'tgaz_wkt_definition': ('TGaz WKT 坐标系定义', 'doc'),
 'tgaz_ck1': ('TGaz 校验表 1', 'guess'),
 'ras_peking_1875_g_1875_bretschneider': ('布列茨奈德 1875《北京图》配准', 'guess'),
 'ras_poddubnyi_1900_pdb2': ('波德布内 1900 西藏图（第2版）', 'guess'),
 'kozlov_1899_mk': ('科兹洛夫 1899 蒙古-康区地图', 'guess'),
 'poddubnyi_1900_tibet': ('波德布内 1900 西藏地图', 'guess'),
 'przh_1871_neimeng': ('普尔热瓦尔斯基 1871 内蒙探险图', 'doc'),
 'przh_1876_tianshan': ('普尔热瓦尔斯基 1876 天山探险图', 'doc'),
 'przh_1884_xj_qh': ('普尔热瓦尔斯基 1884 新疆-青海探险图', 'doc'),
 'przh_1888_tarim': ('普尔热瓦尔斯基 1888 塔里木探险图', 'doc'),
 'teahorse_major_routes': ('茶马古道主路（线）', 'doc'),
 'teahorse_minor_routes': ('茶马古道支路（线）', 'doc'),
 'teahorse_nodes': ('茶马古道节点（点）', 'doc'),
 'tbrc_tbrc_major_monasteries_2014': ('TBRC 大寺院 2014（点）', 'doc'),
 'tbrc_tbrc_minor_monasteries_2014': ('TBRC 小寺院 2014（点）', 'doc'),
 'tbrc_tbrc_printeries_2014': ('TBRC 印经院 2014（点）', 'doc'),
 'tbrc_tibet_monasteries_utf8_v1_20120702': ('TBRC 西藏寺院 2012（UTF8）', 'doc'),
 'china_gas_2013_chinagaspipelines_2013': ('2013 中国天然气管道（线）', 'doc'),
 'china_gas_2013_chinagaslinenodes_2013': ('2013 天然气管网节点（点）', 'doc'),
 'china_hsr_2016_lines': ('2016 中国高铁线路（线）', 'doc'),
 'china_hsr_2016_stations': ('2016 中国高铁车站（点）', 'doc'),
 'citas90_cnty_pgn': ('CITAS 1990 县级面（人口经济）', 'doc'),
 'citas90_pref_pgn': ('CITAS 1990 府级面', 'doc'),
 'citas90_prov_pgn': ('CITAS 1990 省级面', 'doc'),
 'jp_toku_dmyo_pgn': ('日本江户（德川）时代藩领地·面', 'guess'),
 'jp_toku_dmyo_pts': ('日本江户时代藩·点', 'guess'),
 'jp_toku_doo_pgn': ('日本江户时代「道」（区划）·面', 'guess'),
 'jp_toku_kuni_pgn': ('日本江户时代「国」（令制国）·面', 'guess'),
 'arc_china_index_v3': ('CHGIS Arc 平台发布索引 V3', 'guess'),
 'arc_china_index_v4': ('CHGIS Arc 平台发布索引 V4', 'guess'),
 'beijing_historic_sites_v1': ('北京历史遗址 V1', 'doc'),
 'bgis_v1_1_2013': ('BGIS 佛教历史 GIS 2013 底表', 'doc'),
 'chgis_tmpl_pts': ('CHGIS 模板点表', 'guess'),
 'chinaw_pts': ('ChinaW 地名点', 'guess'),
 'dcw_asia_contour': ('DCW 亚洲海岸线/等高线（18.6 万条）', 'ok'),
 'ngia_dsg_codes_2017_03_15': ('NGIA 政区类别代码（2017-03-15）', 'guess'),
 'nima_feat_desig': ('NIMA 特征类型代码表', 'doc'),
 'physiogmacroregions_pgn': ('中国生理大区（面）', 'doc'),
 'tan_tan_gbk_names1': ('谭其骧《中国历史地图集》GBK 地名表（一）', 'doc'),
 'tan_tan_gbk_names2': ('谭其骧《中国历史地图集》GBK 地名表（二）', 'doc'),
 'workshop2001_index': ('2001 CHGIS 工作坊资料索引', 'guess'),
}
_RUSS = {'1871_neimeng':'1871 内蒙','1876_xinjiang':'1876 新疆','1884_qinghai':'1884 青海','1884_tarim':'1884 塔里木',
         '1899_mk':'1899 蒙古-康区','1900_kham':'1900 康区','1904_tibet':'1904 西藏'}

def harv_desc(tb):
    if tb in HARV: return HARV[tb]
    if tb.startswith('russ_'):
        return ('俄国勘探图提取点位 · ' + _RUSS.get(tb[5:], tb[5:]), 'guess')
    if tb.startswith('ras_1926_atlas'):
        return ('俄国地理学会 1926 亚洲图集 · 图幅 ' + tb.split('_')[-1], 'guess')
    if tb.startswith('ras_przh_1876'):
        return ('普尔热瓦尔斯基 1876 天山探险 · 分幅 ' + tb.replace('ras_przh_1876_',''), 'guess')
    if tb.startswith('ras_przh_1884'):
        return ('普尔热瓦尔斯基 1884 探险 · 分幅 ' + tb.replace('ras_przh_1884_',''), 'guess')
    return ('', 'guess')

# ---------- 家族归类 ----------
PUB_FAM_RULES = [
    ('主表与主数据', {'biog_main','addr_codes','text_codes','dynasties','office_codes','nian_hao','ganzhi_codes','year_range_codes'}),
    ('专门数据集', {'quan_yuan_wen_index','china_pop_1999_county','missionary_writings','academies_2957','thdl_tibet_adm_areas','gb_91_codes','merged_person_data','addr_xy','kin_mourning','kin_mourning_steps','possession_data','possession_addr','possession_act_codes','events_data','events_addr'}),
    ('系统表/视图', {'spatial_ref_sys','geography_columns','geometry_columns','raster_columns','raster_overviews'}),
]
def pub_fam(tb):
    for name, s in PUB_FAM_RULES:
        if tb in s: return name
    if tb.endswith(('_codes','_types')) or '_code_type_rel' in tb or tb.endswith('_tree') or tb=='text_type': return '词表与代码'
    if tb.endswith('_data'): return '事实记录'
    if tb.startswith('social_institution'): return '机构数据'
    if tb.startswith('text_') or tb.startswith('biog_text'): return '文献数据'
    return '其他'

def chgis_fam(tb):
    if tb.startswith('hartwell'): return 'Hartwell 复原'
    if tb.startswith('ming'): return '明代地理'
    if tb.startswith('dem') or '_dem_' in tb or tb.endswith('_dem_topo30'): return 'DEM 地形'
    if tb.startswith('v6'): return 'V6（现行版）'
    if tb.startswith('v5'): return 'V5'
    if tb.startswith('v4'): return 'V4'
    if tb.startswith('v3'): return 'V3'
    if tb.startswith('v2'): return 'V2'
    if tb.startswith(('china_chron','major_china')): return '年表与时期'
    return '工作层与其他'

def harv_fam(tb):
    if tb.startswith('tgaz'): return 'TGaz 地名辞典'
    if tb.startswith(('ras_','russ_','przh_','kozlov','poddubnyi')): return '俄国图与探险地图'
    if tb.startswith('teahorse'): return '茶马古道'
    if tb.startswith('tbrc'): return '藏传佛教资源'
    if tb.startswith('china_'): return '现代基础设施'
    if tb.startswith('citas90'): return 'CITAS 1990'
    if tb.startswith('jp_'): return '日本历史政区'
    if tb.startswith(('dcw','nima','ngia','physiog')): return '底图与代码'
    if tb.startswith('tan_tan'): return '谭图 GBK'
    return '其他'

FAMFN = {'public': pub_fam, 'chgis': chgis_fam, 'harv': harv_fam,
         'ogr_system_tables': lambda tb: '系统'}
DESCFN = {'public': lambda tb: PUB.get(tb, ('', 'guess')),
          'chgis': chgis_desc, 'harv': harv_desc,
          'ogr_system_tables': lambda tb: ('GDAL/OGR 系统元数据（图层注册信息）', 'doc') if tb == 'metadata' else ('', 'guess')}

# ---------- 关系推断（命名规约；目标表存在才输出；一律标「推断」） ----------
REL = {
 'c_personid':'biog_main','c_kin_id':'biog_main','c_assoc_id':'biog_main',
 'c_tertiary_personid':'biog_main','c_assoc_claimer_id':'biog_main','c_person_id':'biog_main',
 'c_addr_id':'addr_codes','c_index_addr_id':'addr_codes',
 'c_kin_code':'kinship_codes','c_assoc_kin_code':'kinship_codes',
 'c_assoc_code':'assoc_codes','c_entry_code':'entry_codes','c_office_id':'office_codes',
 'c_textid':'text_codes','c_source':'text_codes','c_dy':'dynasties',
 'c_alt_name_type_code':'altname_codes','c_name_type_code':'altname_codes',
 'c_addr_type':'biog_addr_codes','c_inst_code':'social_institution_codes',
 'c_inst_name_code':'social_institution_name_codes','c_status_code':'status_codes',
 'c_ethnicity_code':'ethnicity_tribe_codes','c_household_status_code':'household_status_codes',
 'c_index_year_type_code':'indexyear_type_codes',
 'c_by_nh_code':'nian_hao','c_dy_nh_code':'nian_hao','c_fy_nh_code':'nian_hao','c_ly_nh_code':'nian_hao',
 'c_assoc_fy_nh_code':'nian_hao','c_assoc_ly_nh_code':'nian_hao','c_entry_nh_code':'nian_hao',
 'c_posting_id':'posting_data','c_appoint_type':'appointment_codes',
 'c_by_range':'year_range_codes','c_dy_range':'year_range_codes',
 'c_fy_range':'year_range_codes','c_ly_range':'year_range_codes',
 'c_assoc_fy_range':'year_range_codes','c_assoc_ly_range':'year_range_codes',
 'c_by_day_gz':'ganzhi_codes','c_dy_day_gz':'ganzhi_codes',
 'c_fy_day_gz':'ganzhi_codes','c_ly_day_gz':'ganzhi_codes',
 'c_assoc_fy_day_gz':'ganzhi_codes','c_assoc_ly_day_gz':'ganzhi_codes',
 'c_choronym_code':'choronym_codes','c_occasion_code':'occasion_codes',
 'c_litgenre_code':'literarygenre_codes','c_topic_code':'scholarlytopic_codes',
 'c_tribe':'ethnicity_tribe_codes','c_country':'country_codes',
 'c_parental_status_code':'parental_status_codes','c_measure':'measure_codes',
}
