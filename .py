import uuid
from lxml import etree

def gen_uid():
    return str(uuid.uuid4())

# Исходные данные (одна организация и один отдел)
org_name = "Организация_1"
dep_name = "Отдел_1"

NSMAP = {
    'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    'md': "http://iec.ch/TC57/61970-552/ModelDescription/1#",
    'cim': "http://monitel.com/2021/schema-access#"
}

# Генерируем все уникальные идентификаторы
folder_uid = input('Введите UID папки для ролей')
role_uid = gen_uid()
privilege_uid = gen_uid()
datagroup_uid = gen_uid()
objectref_uid = gen_uid()
objectref_objectuid = gen_uid()

rdf = etree.Element('{%s}RDF' % NSMAP['rdf'], nsmap=NSMAP)

# -- md:FullModel (заголовок модели) --
fullmodel = etree.SubElement(rdf, '{%s}FullModel' % NSMAP['md'], attrib={
    '{%s}about' % NSMAP['rdf']: '#_' + gen_uid()
})
etree.SubElement(fullmodel, '{%s}Model.created' % NSMAP['md']).text = "2025-08-04T11:17:53.711043Z"
etree.SubElement(fullmodel, '{%s}Model.version' % NSMAP['md']).text = "2025-03-04(11.7.1.7)"
etree.SubElement(fullmodel, '{http://monitel.com/2014/schema-cim16#}Model.name').text = "Access"

# # -- Folder --
# folder = etree.SubElement(rdf, '{%s}Folder' % NSMAP['cim'], attrib={
#     '{%s}about' % NSMAP['rdf']: "#_"+folder_uid
# })
# etree.SubElement(folder, '{%s}IdentifiedObject.name' % NSMAP['cim']).text = (
#     f'Чтение записей по подразделениям\\{org_name}\\{dep_name}'
# )
# etree.SubElement(folder, '{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={
#     '{%s}resource' % NSMAP['rdf']: "#_"+gen_uid()
# })
# etree.SubElement(folder, '{%s}IdentifiedObject.ChildObjects' % NSMAP['cim'], attrib={
#     '{%s}resource' % NSMAP['rdf']: "#_"+role_uid
# })
# etree.SubElement(folder, '{%s}Folder.CreatingNode' % NSMAP['cim'], attrib={
#     '{%s}resource' % NSMAP['rdf']: "#_"+gen_uid()
# })

# -- Role --
role = etree.SubElement(rdf, '{%s}Role' % NSMAP['cim'], attrib={
    '{%s}about' % NSMAP['rdf']: "#_"+role_uid
})
etree.SubElement(role, '{%s}IdentifiedObject.name' % NSMAP['cim']).text = f'Чтение записей под подр-ю {org_name}\{dep_name}'
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

# -- Privilege --
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

# -- DataGroup --
datagr = etree.SubElement(rdf, '{%s}DataGroup' % NSMAP['cim'], attrib={
    '{%s}about' % NSMAP['rdf']: "#_"+datagroup_uid
})
etree.SubElement(datagr, '{%s}IdentifiedObject.name' % NSMAP['cim']).text = f'{org_name}\{dep_name}'
etree.SubElement(datagr, '{%s}IdentifiedObject.ParentObject' % NSMAP['cim'], attrib={
    '{%s}resource' % NSMAP['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"
})
etree.SubElement(datagr, '{%s}DataItem.isHostRestricted' % NSMAP['cim']).text = 'false'
etree.SubElement(datagr, '{%s}DataItem.isUserRestricted' % NSMAP['cim']).text = 'true'
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

# -- ObjectReference --
oref = etree.SubElement(rdf, '{%s}ObjectReference' % NSMAP['cim'], attrib={
    '{%s}about' % NSMAP['rdf']: "#_"+objectref_uid
})
etree.SubElement(oref, '{%s}ObjectReference.objectUid' % NSMAP['cim']).text = objectref_objectuid
etree.SubElement(oref, '{%s}ObjectReference.Group' % NSMAP['cim'], attrib={
    '{%s}resource' % NSMAP['rdf']: "#_"+datagroup_uid
})

# Форматирование и сохранение
etree.indent(rdf, space="  ")
xml_bytes = etree.tostring(rdf, xml_declaration=True, encoding='utf-8', pretty_print=True)
with open("cim_generated_one.xml", "wb") as f:
    f.write(xml_bytes)

print("Готово! RDF XML для одной роли сохранён как cim_generated_one.xml")
