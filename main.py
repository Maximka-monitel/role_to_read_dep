import chardet
import os
import uuid
import csv
from lxml import etree
from datetime import datetime

def gen_uid():
    return str(uuid.uuid4())

def check_required_fields(row, required_fields):
    for field in required_fields:
        val = row.get(field)
        if val is None or not val.strip():
            return False, f"Поле '{field}' отсутствует или пустое"
    return True, ""

def create_rdf_root(NSMAP):
    rdf = etree.Element('{%s}RDF' % NSMAP['rdf'], nsmap=NSMAP)
    fullmodel = etree.SubElement(rdf, '{%s}FullModel' % NSMAP['md'], attrib={
        '{%s}about' % NSMAP['rdf']: '#_' + gen_uid()
    })
    time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    etree.SubElement(fullmodel, '{%s}Model.created' % NSMAP['md']).text = time_str + "Z"
    etree.SubElement(fullmodel, '{%s}Model.version' % NSMAP['md']).text = "2025-03-04(11.7.1.7)"
    etree.SubElement(fullmodel, '{http://monitel.com/2014/schema-cim16#}Model.name').text = "Access"
    return rdf

def add_datagroup_structure(rdf, NSMAP, org_name, dep_name, dep_uid):
    datagroup_uid = gen_uid()
    objectref_uid = gen_uid()
    datagr = etree.SubElement(rdf, '{%s}DataGroup' % NSMAP['cim'], attrib={'{%s}about' % NSMAP['rdf']: "#_" + datagroup_uid})
    etree.SubElement(datagr, '{%s}IdentifiedObject.name' % NSMAP['cim']).text = f'{org_name}\\{dep_name}'
    etree.SubElement(datagr, '{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"})
    etree.SubElement(datagr, '{%s}DataItem.isHostRestricted' % NSMAP['cim']).text = 'false'
    etree.SubElement(datagr, '{%s}DataItem.isUserRestricted' % NSMAP['cim']).text = 'true'
    etree.SubElement(datagr, '{%s}DataItem.Category' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_20000db8-0000-0000-c000-0000006d746c"})
    etree.SubElement(datagr, '{%s}DataGroup.Class' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"})
    etree.SubElement(datagr, '{%s}DataGroup.Objects' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + objectref_uid})
    oref = etree.SubElement(rdf, '{%s}ObjectReference' % NSMAP['cim'], attrib={'{%s}about' % NSMAP['rdf']: "#_" + objectref_uid})
    etree.SubElement(oref, '{%s}ObjectReference.objectUid' % NSMAP['cim']).text = dep_uid
    etree.SubElement(oref, '{%s}ObjectReference.Group' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + datagroup_uid})
    return datagroup_uid

def add_role_structure_multiple_datagroups(rdf, NSMAP, org_name, dep_name, folder_uid, datagroup_uids):
    role_uid = gen_uid()
    privilege_uid = gen_uid()
    role = etree.SubElement(rdf, '{%s}Role' % NSMAP['cim'], attrib={
        '{%s}about' % NSMAP['rdf']: "#_" + role_uid
    })
    etree.SubElement(role, '{%s}IdentifiedObject.name' % NSMAP['cim']).text = f'Чтение записей под подр-ю {org_name}\\{dep_name}'
    etree.SubElement(role, '{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + folder_uid})
    etree.SubElement(role, '{%s}Role.isHost' % NSMAP['cim']).text = 'false'
    etree.SubElement(role, '{%s}Role.isUser' % NSMAP['cim']).text = 'true'
    etree.SubElement(role, '{%s}Role.kind' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "cim:RoleKind.allow"})
    etree.SubElement(role, '{%s}Role.Privileges' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + privilege_uid})
    priv = etree.SubElement(rdf, '{%s}Privilege' % NSMAP['cim'], attrib={'{%s}about' % NSMAP['rdf']: "#_" + privilege_uid})
    etree.SubElement(priv, '{%s}Privilege.Role' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + role_uid})
    for dg_uid in datagroup_uids:
        etree.SubElement(priv, '{%s}Privilege.DataItems' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_" + dg_uid})
    etree.SubElement(priv, '{%s}Privilege.Operation' % NSMAP['cim'], attrib={'{%s}resource' % NSMAP['rdf']: "#_2000065d-0000-0000-c000-0000006d746c"})

def process_all_csv_from_list(folder_uid, csv_dir, file_list, log_callback=None):
    NSMAP = {
        'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        'md': "http://iec.ch/TC57/61970-552/ModelDescription/1#",
        'cim': "http://monitel.com/2021/schema-access#"
    }
    required_fields = ['org_name', 'dep_name', 'dep_uid']

    for csv_filename in file_list:
        xml_filename = os.path.splitext(csv_filename)[0] + '.xml'
        log_prefix = f"[{csv_filename}] "
        try:
            # --- Анализируем структуру файла -----
            csv_file_path = os.path.join(csv_dir, csv_filename)
            with open(csv_file_path, 'rb') as f:
                rawdata = f.read(10000)
                detected = chardet.detect(rawdata)
                enc = detected['encoding']
            if log_callback:
                log_callback(f"{log_prefix}Открытие файла в кодировке: {enc}\n")

            dep_rows = []
            dep_headdep = {}      # dep_uid -> dep_headdep_uid
            dep_info = {}         # dep_uid -> (org_name, dep_name)
            with open(csv_file_path, encoding=enc) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                for row in reader:
                    ok, err_msg = check_required_fields(row, required_fields)
                    if not ok:
                        continue
                    dep_uid = row['dep_uid']
                    dep_name = row['dep_name']
                    dep_headdep_uid = row.get('dep_headdep_uid', '').strip()
                    org_name = row.get('org_name', '')
                    dep_rows.append(row)
                    dep_headdep[dep_uid] = dep_headdep_uid
                    dep_info[dep_uid] = (org_name, dep_name)

            # 2. Найти headdep_uid'ы — те кто встречается в значении dep_headdep_uid хотя бы раз
            headdep_uids = set(filter(None, [row.get('dep_headdep_uid', '').strip() for row in dep_rows]))

            # 3. Для headdep ищем все департаменты, которыми он "руководит"
            dep_children = {}  # headdep_uid -> [dep_uid,...]
            for row in dep_rows:
                d_uid = row['dep_uid']
                hd_uid = row.get('dep_headdep_uid', '').strip()
                if hd_uid:
                    dep_children.setdefault(hd_uid, []).append(d_uid)

            # 4. Создать datagroup для каждого отдела
            rdf = create_rdf_root(NSMAP)
            datagroup_map = {}  # dep_uid -> datagroup_uid
            for dep_uid, (org_name, dep_name) in dep_info.items():
                datagroup_uid = add_datagroup_structure(rdf, NSMAP, org_name, dep_name, dep_uid)
                datagroup_map[dep_uid] = datagroup_uid

            # 5. Создать role для каждого отдела — обычную или headdep
            for dep_uid, (org_name, dep_name) in dep_info.items():
                if dep_uid in headdep_uids:
                    under_deps = dep_children.get(dep_uid, [])
                    accessible = set(under_deps)
                    accessible.add(dep_uid)
                    datagroup_uids = [datagroup_map[x] for x in accessible if x in datagroup_map]
                    add_role_structure_multiple_datagroups(rdf, NSMAP, org_name, dep_name, folder_uid, datagroup_uids)
                    if log_callback:
                        log_callback(f"{log_prefix}{dep_uid}: headdep, доступ к {len(datagroup_uids)} департаментам\n")
                else:
                    add_role_structure_multiple_datagroups(rdf, NSMAP, org_name, dep_name, folder_uid, [datagroup_map[dep_uid]])
                    if log_callback:
                        log_callback(f"{log_prefix}{dep_uid}: обычный департамент\n")

            # Сохраняем XML
            etree.indent(rdf, space="  ")
            xml_bytes = etree.tostring(rdf, xml_declaration=True, encoding='utf-8', pretty_print=True)
            out_path = os.path.join(csv_dir, xml_filename)
            with open(out_path, "wb") as f:
                f.write(xml_bytes)
            if log_callback:
                log_callback(f"{log_prefix}Готово! {xml_filename} сформирован из {csv_filename}\n")
        except Exception as e:
            if log_callback:
                log_callback(f"{log_prefix}Критическая ошибка: {e}\n")
