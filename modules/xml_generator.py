"""
Модуль генерации XML файлов в формате RDF
Масштабируемый для любого проекта
"""

import uuid
from datetime import datetime
import lxml.etree as etree
from lxml.etree import xmlfile
from typing import Dict, List, Callable
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
        self.default_model_version = "1.0.0"
        self.default_model_name = "GeneratedModel"

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
            # Добавляем XML декларацию и processing instructions
            xf.write_declaration()
            # Note: processing instructions нужно добавить отдельно

            with xf.element('{%s}RDF' % self.namespaces['rdf'], nsmap=self.namespaces):
                content_generator(xf)

    def _add_newline(self, xf: xmlfile) -> None:
        """Добавляет перенос строки."""
        xf.write('\n')

    def add_full_model(
        self,
        xf: xmlfile,
        model_version: str = None,
        model_name: str = None,
        additional_elements: List[Dict] = None
    ) -> str:
        """
        Добавляет элемент FullModel с метаданными.
        """
        model_uid = gen_uid()
        model_version = model_version or self.default_model_version
        model_name = model_name or self.default_model_name

        with xf.element('{%s}FullModel' % self.namespaces.get('md', ''),
                        attrib={'{%s}about' % self.namespaces['rdf']: '#_' + model_uid}):
            time_str = datetime.now().strftime(
                '%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z"

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
                me_ns = me_namespace
                with xf.element('{%s}Model.name' % me_ns, nsmap={'me': me_ns}):
                    xf.write(model_name)
            else:
                # fallback если не указано в config
                with xf.element('{%s}Model.name' % self.namespaces.get('md', '')):
                    xf.write(model_name)
            self._add_newline(xf)

            # Добавляем дополнительные элементы если указаны
            if additional_elements:
                for elem in additional_elements:
                    ns = elem.get('namespace', 'md')
                    ns_uri = self.namespaces.get(ns, '')
                    with xf.element('{%s}%s' % (ns_uri, elem['name'])):
                        if elem.get('text'):
                            xf.write(elem.get('text', ''))
                    self._add_newline(xf)

        self._add_newline(xf)
        return model_uid

    def add_custom_element(
        self,
        xf: xmlfile,
        element_name: str,
        namespace: str,
        attributes: Dict[str, str] = None,
        text: str = None,
        child_elements: List[Dict] = None
    ) -> None:
        """
        Добавляет пользовательский элемент XML.
        """
        ns_uri = self.namespaces.get(namespace, '')
        attrib = attributes or {}

        # Обрабатываем RDF атрибуты правильно
        processed_attrib = {}
        for attr_name, attr_value in attrib.items():
            if attr_name.startswith('{'):
                processed_attrib[attr_name] = attr_value
            elif ':' in attr_name:
                prefix, local_name = attr_name.split(':', 1)
                if prefix in self.namespaces:
                    processed_attrib['{%s}%s' % (
                        self.namespaces[prefix], local_name)] = attr_value
                else:
                    processed_attrib[attr_name] = attr_value
            else:
                processed_attrib[attr_name] = attr_value

        if child_elements:
            with xf.element('{%s}%s' % (ns_uri, element_name), attrib=processed_attrib):
                if text:
                    xf.write(text)
                for child in child_elements:
                    self.add_custom_element(
                        xf, child['name'], child['namespace'],
                        child.get('attributes'), child.get('text'),
                        child.get('child_elements')
                    )
                    self._add_newline(xf)
        else:
            if text is not None:
                with xf.element('{%s}%s' % (ns_uri, element_name), attrib=processed_attrib):
                    xf.write(text)
            else:
                # Для элементов с атрибутами используем etree.Element
                element = etree.Element('{%s}%s' % (
                    ns_uri, element_name), attrib=processed_attrib)
                xf.write(element)
            self._add_newline(xf)


class AccessXMLGenerator(XMLGenerator):
    """Специализированный генератор XML для системы доступа."""

    def __init__(self):
        """Инициализация генератора для системы доступа."""
        super().__init__()
        # Все namespaces теперь берутся из config.json

    def add_object_reference(
        self,
        xf: xmlfile,
        object_uid: str,
        group_uid: str,
        reference_uid: str = None
    ) -> str:
        """
        Добавляет элемент ObjectReference.
        """
        ref_uid = reference_uid or gen_uid()
        attrib = {'{%s}about' % self.namespaces['rdf']: "#_" + ref_uid}

        with xf.element('{%s}ObjectReference' % self.namespaces['cim'], attrib=attrib):
            # Используем xf.element и xf.write для правильных префиксов
            with xf.element('{%s}ObjectReference.objectUid' % self.namespaces['cim']):
                xf.write(object_uid)
            self._add_newline(xf)

            group_attrib = {'{%s}resource' %
                            self.namespaces['rdf']: "#_" + group_uid}
            with xf.element('{%s}ObjectReference.Group' % self.namespaces['cim'], attrib=group_attrib):
                pass
            self._add_newline(xf)

        self._add_newline(xf)
        return ref_uid

    def add_data_group(
        self,
        xf: xmlfile,
        group_uid: str,
        group_name: str,
        parent_uid: str = None,
        additional_attributes: Dict = None,
        additional_elements: List[Dict] = None,
        privilege_uid: str = None
    ) -> str:
        """
        Добавляет элемент DataGroup.
        """
        data_group_uid = group_uid or gen_uid()
        attrib = {'{%s}about' % self.namespaces['rdf']: "#_" + data_group_uid}

        with xf.element('{%s}DataGroup' % self.namespaces['cim'], attrib=attrib):
            # Используем xf.element для правильных префиксов
            with xf.element('{%s}IdentifiedObject.name' % self.namespaces['cim']):
                xf.write(group_name)
            self._add_newline(xf)

            # Обязательный ParentObject
            parent_resource = parent_uid or "#_50000dc6-0000-0000-c000-0000006d746c"
            parent_attrib = {'{%s}resource' %
                             self.namespaces['rdf']: parent_resource}
            with xf.element('{%s}IdentifiedObject.ParentObject' % self.namespaces['cim'], attrib=parent_attrib):
                pass
            self._add_newline(xf)

            # Добавляем стандартные атрибуты
            with xf.element('{%s}DataItem.isHostRestricted' % self.namespaces['cim']):
                xf.write('false')
            self._add_newline(xf)

            with xf.element('{%s}DataItem.isUserRestricted' % self.namespaces['cim']):
                xf.write('true')
            self._add_newline(xf)

            # Добавляем обязательные элементы
            if privilege_uid:
                priv_attrib = {'{%s}resource' %
                               self.namespaces['rdf']: "#_" + privilege_uid}
                with xf.element('{%s}DataItem.Privileges' % self.namespaces['cim'], attrib=priv_attrib):
                    pass
                self._add_newline(xf)

            # Обязательный Category
            category_attrib = {
                '{%s}resource' % self.namespaces['rdf']: "#_20000db8-0000-0000-c000-0000006d746c"}
            with xf.element('{%s}DataItem.Category' % self.namespaces['cim'], attrib=category_attrib):
                pass
            self._add_newline(xf)

            # Обязательный DataGroup.Class
            class_attrib = {
                '{%s}resource' % self.namespaces['rdf']: "#_50000dc6-0000-0000-c000-0000006d746c"}
            with xf.element('{%s}DataGroup.Class' % self.namespaces['cim'], attrib=class_attrib):
                pass
            self._add_newline(xf)

            # Добавляем дополнительные атрибуты если указаны
            if additional_attributes:
                for key, value in additional_attributes.items():
                    with xf.element('{%s}%s' % (self.namespaces['cim'], key)):
                        xf.write(value)
                    self._add_newline(xf)

            # Добавляем дополнительные элементы если указаны
            if additional_elements:
                for elem in additional_elements:
                    ns = elem.get('namespace', 'cim')
                    ns_uri = self.namespaces.get(ns, '')
                    attrib_dict = {}
                    if elem.get('resource'):
                        attrib_dict['{%s}resource' %
                                    self.namespaces['rdf']] = elem['resource']
                    with xf.element('{%s}%s' % (ns_uri, elem['name']), attrib=attrib_dict):
                        pass
                    self._add_newline(xf)

        self._add_newline(xf)
        return data_group_uid

    def add_role_with_privilege(
        self,
        xf: xmlfile,
        role_name: str,
        parent_uid: str,
        data_items_uids: List[str],
        operation_uid: str = "#_2000065d-0000-0000-c000-0000006d746c",
        role_kind: str = "cim:RoleKind.allow"
    ) -> tuple:
        """
        Добавляет роль с привилегиями.

        Returns:
            tuple: (role_uid, privilege_uid)
        """
        role_uid = gen_uid()
        privilege_uid = gen_uid()

        # Добавляем роль
        with xf.element('{%s}Role' % self.namespaces['cim'],
                        attrib={'{%s}about' % self.namespaces['rdf']: "#_" + role_uid}):
            with xf.element('{%s}IdentifiedObject.name' % self.namespaces['cim']):
                xf.write(role_name)
            self._add_newline(xf)

            # Используем xf.element для правильных префиксов
            parent_attrib = {'{%s}resource' %
                             self.namespaces['rdf']: "#_" + parent_uid}
            with xf.element('{%s}IdentifiedObject.ParentObject' % self.namespaces['cim'], attrib=parent_attrib):
                pass
            self._add_newline(xf)

            with xf.element('{%s}Role.isHost' % self.namespaces['cim']):
                xf.write('false')
            self._add_newline(xf)

            with xf.element('{%s}Role.isUser' % self.namespaces['cim']):
                xf.write('true')
            self._add_newline(xf)

            priv_attrib = {'{%s}resource' %
                           self.namespaces['rdf']: "#_" + privilege_uid}
            with xf.element('{%s}Role.Privileges' % self.namespaces['cim'], attrib=priv_attrib):
                pass
            self._add_newline(xf)

        self._add_newline(xf)

        # Добавляем привилегию
        with xf.element('{%s}Privilege' % self.namespaces['cim'],
                        attrib={'{%s}about' % self.namespaces['rdf']: "#_" + privilege_uid}):
            role_attrib = {'{%s}resource' %
                           self.namespaces['rdf']: "#_" + role_uid}
            with xf.element('{%s}Privilege.Role' % self.namespaces['cim'], attrib=role_attrib):
                pass
            self._add_newline(xf)

            # Добавляем ссылки на элементы данных
            for item_uid in data_items_uids:
                data_attrib = {'{%s}resource' %
                               self.namespaces['rdf']: "#_" + item_uid}
                with xf.element('{%s}Privilege.DataItems' % self.namespaces['cim'], attrib=data_attrib):
                    pass
                self._add_newline(xf)

            operation_attrib = {'{%s}resource' %
                                self.namespaces['rdf']: operation_uid}
            with xf.element('{%s}Privilege.Operation' % self.namespaces['cim'], attrib=operation_attrib):
                pass
            self._add_newline(xf)

        self._add_newline(xf)
        return role_uid, privilege_uid


# Фабричные функции для обратной совместимости
def create_access_generator() -> AccessXMLGenerator:
    """Создает генератор для системы доступа."""
    return AccessXMLGenerator()


def create_custom_generator(namespaces: Dict[str, str]) -> XMLGenerator:
    """Создает кастомный генератор XML."""
    generator = XMLGenerator()
    if namespaces:
        generator.namespaces.update(namespaces)
    return generator
