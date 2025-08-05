import chardet
import os
import uuid
import csv
from lxml import etree  # type: ignore
import logging
from datetime import datetime
import sys


def gen_uid():
    return str(uuid.uuid4())


def check_required_fields(row, required_fields):
    for field in required_fields:
        val = row.get(field)
        if val is None or not val.strip():
            return False, f"Поле '{field}' отсутствует или пустое"
    return True, ""


def add_role_structure(rdf, NSMAP, org_name, dep_name, dep_uid, folder_uid):
    role_uid = gen_uid()
    privilege_uid = gen_uid()
    datagroup_uid = gen_uid()
    objectref_uid = gen_uid()

    role = etree.SubElement(rdf, '{%s}Role' % NSMAP['cim'], attrib={
        '{%s}about' % NSMAP['rdf']: "#_"+role_uid
    })
    etree.SubElement(role, '{%s}IdentifiedObject.name' %
                     NSMAP['cim']).text = f'Чтение записей под подр-ю {org_name}\\{dep_name}'
    etree.SubElement(role, '{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_"+folder_uid
    })
    etree.SubElement(role, '{%s}Role.isHost' % NSMAP['cim']).text = 'false'
    etree.SubElement(role, '{%s}Role.isUser' % NSMAP['cim']).text = 'true'
    etree.SubElement(role, '{%s}Role.kind' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "cim:RoleKind.allow"
    })
    etree.SubElement(role, '{%s}Role.Privileges' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_"+privilege_uid
    })

    priv = etree.SubElement(rdf, '{%s}Privilege' % NSMAP['cim'], attrib={
        '{%s}about' % NSMAP['rdf']: "#_"+privilege_uid
    })
    etree.SubElement(priv, '{%s}Privilege.Role' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_"+role_uid
    })
    etree.SubElement(priv, '{%s}Privilege.DataItems' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_"+datagroup_uid
    })
    etree.SubElement(priv, '{%s}Privilege.Operation' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_2000065d-0000-0000-c000-0000006d746c"
    })

    datagr = etree.SubElement(rdf, '{%s}DataGroup' % NSMAP['cim'], attrib={
        '{%s}about' % NSMAP['rdf']: "#_"+datagroup_uid
    })
    etree.SubElement(datagr, '{%s}IdentifiedObject.name' %
                     NSMAP['cim']).text = f'{org_name}\\{dep_name}'
    etree.SubElement(datagr, '{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"
    })
    etree.SubElement(datagr, '{%s}DataItem.isHostRestricted' %
                     NSMAP['cim']).text = 'false'
    etree.SubElement(datagr, '{%s}DataItem.isUserRestricted' %
                     NSMAP['cim']).text = 'true'
    etree.SubElement(datagr, '{%s}DataItem.Privileges' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_"+privilege_uid
    })
    etree.SubElement(datagr, '{%s}DataItem.Category' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_20000db8-0000-0000-c000-0000006d746c"
    })
    etree.SubElement(datagr, '{%s}DataGroup.Class' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"
    })
    etree.SubElement(datagr, '{%s}DataGroup.Objects' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_"+objectref_uid
    })

    oref = etree.SubElement(rdf, '{%s}ObjectReference' % NSMAP['cim'], attrib={
        '{%s}about' % NSMAP['rdf']: "#_"+objectref_uid
    })
    etree.SubElement(oref, '{%s}ObjectReference.objectUid' %
                     NSMAP['cim']).text = dep_uid
    etree.SubElement(oref, '{%s}ObjectReference.Group' % NSMAP['cim'], attrib={
        '{%s}resource' % NSMAP['rdf']: "#_"+datagroup_uid
    })

    return role_uid, privilege_uid, datagroup_uid, objectref_uid


def create_rdf_root(NSMAP):
    rdf = etree.Element('{%s}RDF' % NSMAP['rdf'], nsmap=NSMAP)
    fullmodel = etree.SubElement(rdf, '{%s}FullModel' % NSMAP['md'], attrib={
        '{%s}about' % NSMAP['rdf']: '#_' + gen_uid()
    })
    time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    etree.SubElement(fullmodel, '{%s}Model.created' %
                     NSMAP['md']).text = time_str + "Z"
    etree.SubElement(fullmodel, '{%s}Model.version' %
                     NSMAP['md']).text = "2025-03-04(11.7.1.7)"
    etree.SubElement(
        fullmodel, '{http://monitel.com/2014/schema-cim16#}Model.name').text = "Access"
    return rdf


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
            rdf = create_rdf_root(NSMAP)
            count = 0
            csv_file_path = os.path.join(csv_dir, csv_filename)
            with open(csv_file_path, 'rb') as f:
                rawdata = f.read(10000)
                detected = chardet.detect(rawdata)
                enc = detected['encoding']
            if log_callback:
                log_callback(
                    f"{log_prefix}Открытие файла в кодировке: {enc}\n")
            with open(csv_file_path, encoding=enc) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=';')
                for line_num, row in enumerate(reader, start=2):
                    ok, err_msg = check_required_fields(row, required_fields)
                    if not ok:
                        if log_callback:
                            log_callback(
                                f"{log_prefix}Строка {line_num}: {err_msg}. Строка: {row}\n")
                        continue
                    try:
                        org_name = row['org_name']
                        dep_name = row['dep_name']
                        dep_uid = row['dep_uid']
                        add_role_structure(
                            rdf, NSMAP, org_name, dep_name, dep_uid, folder_uid)
                        count += 1
                        if log_callback:
                            log_callback(
                                f"{log_prefix}Строка {line_num}: Добавлена роль для {org_name}\\{dep_name}, dep_uid={dep_uid}\n")
                    except Exception as e:
                        if log_callback:
                            log_callback(
                                f"{log_prefix}Строка {line_num}: Ошибка формирования XML: {e}\n")
            # Сохраняем XML в ту же папку
            etree.indent(rdf, space="  ")
            xml_bytes = etree.tostring(
                rdf, xml_declaration=True, encoding='utf-8', pretty_print=True)
            out_path = os.path.join(csv_dir, xml_filename)
            with open(out_path, "wb") as f:
                f.write(xml_bytes)
            if log_callback:
                log_callback(
                    f"{log_prefix}Готово! {xml_filename} сформирован из {csv_filename}. Всего ролей: {count}\n")
        except Exception as e:
            if log_callback:
                log_callback(f"{log_prefix}Критическая ошибка: {e}\n")


def process_all_csv_cli():
    """Запуск из командной строки: python main.py <UID> <папка с csv> (или без аргументов — диалоговый режим)"""
    import glob
    if len(sys.argv) >= 3:
        folder_uid = sys.argv[1]
        csv_dir = sys.argv[2]
    else:
        folder_uid = input('Введите UID папки для ролей: ').strip()
        csv_dir = input(
            'Укажите папку, где искать csv-файлы (или . для текущей): ').strip() or '.'
    if not os.path.isdir(csv_dir):
        print(f"Папка не найдена: {csv_dir}")
        return
    # Ищем csv-файлы
    files = [
        f for f in os.listdir(csv_dir)
        if f.lower().endswith('.csv') and f.lower() != 'sample.csv'
    ]
    if not files:
        print("Нет подходящих .csv файлов в указанной папке.")
        return

    print("Будут обработаны файлы:")
    for f in files:
        print("  ", f)
    print("------")

    def cli_log(msg):
        print(msg, end="")

    process_all_csv_from_list(folder_uid, csv_dir, files, log_callback=cli_log)
    print("Готово.")


if __name__ == '__main__':
    process_all_csv_cli()
