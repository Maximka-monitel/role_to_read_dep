"""
Модуль генерации XML файлов в формате RDF
Масштабируемый для любого проекта
"""

import uuid
from datetime import datetime
import lxml.etree as etree
from lxml.etree import xmlfile
from typing import Dict, List, Callable, Tuple
from .config_manager import get_config_value


def gen_uid() -> str:
    """Генерирует уникальный идентификатор."""
    return str(uuid.uuid4())


class XMLGenerator:
    """Генератор XML файлов с настраиваемыми параметрами."""

    def __init__(self, namespaces: Dict[str, str] = None):
        """
        Инициализация генератора XML.
        """
        # Загружаем namespaces из config.json
        self.namespaces = get_config_value('xml_generation.namespaces') or {}
        self.default_model_version = get_config_value(
            'csv_processing.model_version') or "1.0.0"
        self.default_model_name = get_config_value(
            'csv_processing.model_name') or "GeneratedModel"

    def generate_xml(
        self,
        output_file: str,
        content_generator: Callable,
        encoding: str = 'utf-8'
    ) -> None:
        """
        Генерирует XML файл используя переданный генератор контента.
        """
        with xmlfile(output_file, encoding=encoding) as xf:
            # Добавляем XML декларацию
            xf.write_declaration()

            with xf.element('{%s}RDF' % self.namespaces['rdf'], nsmap=self.namespaces):
                content_generator(xf)

    def _add_newline(self, xf: xmlfile) -> None:
        """Добавляет перенос строки."""
        xf.write('\n')

    def add_full_model(
        self,
        xf: xmlfile,
        model_version: str = None,
        model_name: str = None
    ) -> str:
        """
        Добавляет элемент FullModel с метаданными.
        """
        model_uid = gen_uid()
        model_version = model_version or self.default_model_version
        model_name = model_name or self.default_model_name

        with xf.element('{%s}FullModel' % self.namespaces.get('md', ''),
                        attrib={'{%s}about' % self.namespaces['rdf']: '#_' + model_uid}):
            time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + "Z"

            # Используем xf.element для правильных префиксов
            with xf.element('{%s}Model.created' % self.namespaces.get('md', '')):
                xf.write(time_str)
            self._add_newline(xf)

            with xf.element('{%s}Model.version' % self.namespaces.get('md', '')):
                xf.write(model_version)
            self._add_newline(xf)

            # Добавляем Model.name с пространством имен из config
            me_namespace = get_config_value('xml_generation.me_namespace')
            if me_namespace:
                with xf.element('{%s}Model.name' % me_namespace, nsmap={'me': me_namespace}):
                    xf.write(model_name)
            else:
                # fallback если не указано в config
                with xf.element('{%s}Model.name' % self.namespaces.get('md', '')):
                    xf.write(model_name)
            self._add_newline(xf)

        self._add_newline(xf)
        return model_uid


class AccessXMLGenerator(XMLGenerator):
    """Специализированный генератор XML для системы доступа."""

    def __init__(self):
        """Инициализация генератора для системы доступа."""
        super().__init__()

    def add_data_group(
        self,
        xf: xmlfile,
        org_name: str,
        dep_name: str,
        dep_uid: str,
        datagroup_uid: str = None,
        headdep_name: str = None  # Добавлен параметр
    ) -> Tuple[str, str]:
        """
        Добавляет DataGroup и связанный ObjectReference.

        Args:
            xf: xmlfile объект
            org_name: название организации
            dep_name: название подразделения
            dep_uid: UID подразделения
            datagroup_uid: UID группы данных (опционально)
            headdep_name: название головного подразделения (опционально)

        Returns:
            Tuple[str, str]: (datagroup_uid, objectref_uid)
        """
        dg_uid = datagroup_uid or gen_uid()
        objectref_uid = gen_uid()

        # Добавляем DataGroup
        dg_attrib = {'{%s}about' % self.namespaces['rdf']: "#_" + dg_uid}
        with xf.element('{%s}DataGroup' % self.namespaces['cim'], attrib=dg_attrib):
            # IdentifiedObject.name - формируем с учетом иерархии
            org_name_str = org_name if isinstance(
                org_name, str) else str(org_name)
            dep_name_str = dep_name if isinstance(
                dep_name, str) else str(dep_name)

            if headdep_name:
                # Формат с головным подразделением
                headdep_name_str = headdep_name if isinstance(
                    headdep_name, str) else str(headdep_name)
                full_name = f'{org_name_str}\\{headdep_name_str}\\{dep_name_str}'
            else:
                # Формат без головного подразделения
                full_name = f'{org_name_str}\\{dep_name_str}'

            with xf.element('{%s}IdentifiedObject.name' % self.namespaces['cim']):
                xf.write(full_name)
            self._add_newline(xf)

            # IdentifiedObject.ParentObject (фиксированное значение)
            parent_attrib = {
                '{%s}resource' % self.namespaces['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"}
            with xf.element('{%s}IdentifiedObject.ParentObject' % self.namespaces['cim'], attrib=parent_attrib):
                pass
            self._add_newline(xf)

            # DataItem.isHostRestricted
            with xf.element('{%s}DataItem.isHostRestricted' % self.namespaces['cim']):
                xf.write('false')
            self._add_newline(xf)

            # DataItem.isUserRestricted
            with xf.element('{%s}DataItem.isUserRestricted' % self.namespaces['cim']):
                xf.write('true')
            self._add_newline(xf)

            # DataItem.Category (фиксированное значение)
            category_attrib = {
                '{%s}resource' % self.namespaces['rdf']: "#_20000db8-0000-0000-c000-0000006d746c"}
            with xf.element('{%s}DataItem.Category' % self.namespaces['cim'], attrib=category_attrib):
                pass
            self._add_newline(xf)

            # DataGroup.Class (фиксированное значение)
            class_attrib = {
                '{%s}resource' % self.namespaces['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"}
            with xf.element('{%s}DataGroup.Class' % self.namespaces['cim'], attrib=class_attrib):
                pass
            self._add_newline(xf)

            # DataGroup.Objects (связь с ObjectReference)
            objects_attrib = {'{%s}resource' %
                              self.namespaces['rdf']: "#_" + objectref_uid}
            with xf.element('{%s}DataGroup.Objects' % self.namespaces['cim'], attrib=objects_attrib):
                pass
            self._add_newline(xf)

        self._add_newline(xf)

        # Добавляем ObjectReference
        or_attrib = {'{%s}about' %
                     self.namespaces['rdf']: "#_" + objectref_uid}
        with xf.element('{%s}ObjectReference' % self.namespaces['cim'], attrib=or_attrib):
            # ObjectReference.objectUid
            with xf.element('{%s}ObjectReference.objectUid' % self.namespaces['cim']):
                xf.write(dep_uid)
            self._add_newline(xf)

            # ObjectReference.Group (связь с DataGroup)
            group_attrib = {'{%s}resource' %
                            self.namespaces['rdf']: "#_" + dg_uid}
            with xf.element('{%s}ObjectReference.Group' % self.namespaces['cim'], attrib=group_attrib):
                pass
            self._add_newline(xf)

        self._add_newline(xf)

        return dg_uid, objectref_uid

    def add_role_with_privilege(
        self,
        xf: xmlfile,
        org_name: str,
        dep_name: str,
        folder_uid: str,
        datagroup_uids: List[str] = None,
        headdep_name: str = None
    ) -> Tuple[str, str]:
        # Обеспечиваем совместимость с возможными вызовами без datagroup_uids
        if datagroup_uids is None:
            datagroup_uids = []

        r_uid = gen_uid()
        privilege_uid = gen_uid()

        # Определение шаблона
        if headdep_name:
            # Используем шаблон из конфига для случая с HeadDepartment
            role_template = get_config_value('csv_processing.role_template_with_headdep') or \
                "Чтение записей по подр-ю {org_name}\\{headdep_name}\\{dep_name}"
        else:
            # Используем стандартный шаблон
            role_template = get_config_value('csv_processing.role_template') or \
                "Чтение записей по подр-ю {org_name}\\{dep_name}"

        # Добавляем Role
        role_attrib = {'{%s}about' % self.namespaces['rdf']: "#_" + r_uid}
        with xf.element('{%s}Role' % self.namespaces['cim'], attrib=role_attrib):
            # IdentifiedObject.name
            org_name_str = org_name if isinstance(
                org_name, str) else str(org_name)
            dep_name_str = dep_name if isinstance(
                dep_name, str) else str(dep_name)

            if headdep_name:
                headdep_name_str = headdep_name if isinstance(
                    headdep_name, str) else str(headdep_name)
                role_name = role_template.format(
                    org_name=org_name_str,
                    headdep_name=headdep_name_str,
                    dep_name=dep_name_str
                )
            else:
                role_name = role_template.format(
                    org_name=org_name_str,
                    dep_name=dep_name_str
                )

            with xf.element('{%s}IdentifiedObject.name' % self.namespaces['cim']):
                xf.write(role_name)
            self._add_newline(xf)

            # IdentifiedObject.ParentObject
            parent_attrib = {'{%s}resource' %
                             self.namespaces['rdf']: "#_" + folder_uid}
            with xf.element('{%s}IdentifiedObject.ParentObject' % self.namespaces['cim'], attrib=parent_attrib):
                pass
            self._add_newline(xf)

            # Role.isHost
            with xf.element('{%s}Role.isHost' % self.namespaces['cim']):
                xf.write('false')
            self._add_newline(xf)

            # Role.isUser
            with xf.element('{%s}Role.isUser' % self.namespaces['cim']):
                xf.write('true')
            self._add_newline(xf)

            # Role.kind
            kind_attrib = {'{%s}resource' %
                           self.namespaces['rdf']: "cim:RoleKind.allow"}
            with xf.element('{%s}Role.kind' % self.namespaces['cim'], attrib=kind_attrib):
                pass
            self._add_newline(xf)

            # Role.Privileges (связь с Privilege)
            priv_attrib = {'{%s}resource' %
                           self.namespaces['rdf']: "#_" + privilege_uid}
            with xf.element('{%s}Role.Privileges' % self.namespaces['cim'], attrib=priv_attrib):
                pass
            self._add_newline(xf)

        self._add_newline(xf)

        # Добавляем Privilege
        priv_attrib = {'{%s}about' %
                       self.namespaces['rdf']: "#_" + privilege_uid}
        with xf.element('{%s}Privilege' % self.namespaces['cim'], attrib=priv_attrib):
            # Privilege.Role (связь с Role)
            role_link_attrib = {'{%s}resource' %
                                self.namespaces['rdf']: "#_" + r_uid}
            with xf.element('{%s}Privilege.Role' % self.namespaces['cim'], attrib=role_link_attrib):
                pass
            self._add_newline(xf)

            # Privilege.DataItems (связи с DataGroups)
            for dg_uid in datagroup_uids:
                data_attrib = {'{%s}resource' %
                               self.namespaces['rdf']: "#_" + dg_uid}
                with xf.element('{%s}Privilege.DataItems' % self.namespaces['cim'], attrib=data_attrib):
                    pass
                self._add_newline(xf)

            # Privilege.Operation (фиксированное значение)
            operation_attrib = {
                '{%s}resource' % self.namespaces['rdf']: "#_2000065d-0000-0000-c000-0000006d746c"}
            with xf.element('{%s}Privilege.Operation' % self.namespaces['cim'], attrib=operation_attrib):
                pass
            self._add_newline(xf)

        self._add_newline(xf)

        return r_uid, privilege_uid


# Фабричные функции для обратной совместимости
def create_access_generator() -> AccessXMLGenerator:
    """Создает генератор для системы доступа."""
    return AccessXMLGenerator()
