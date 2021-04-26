from stdnum import get_cc_module
import stdnum.exceptions
from sql import Null, Column, Literal
from sql.functions import CharLength, Substring, Position
from sql.operators import Equal
from PIL import Image, ExifTags
from io import BytesIO

from trytond.i18n import gettext
from trytond.model import (ModelView, ModelSQL, MultiValueMixin, ValueMixin,
    DeactivableMixin, fields, Unique, sequence_ordered, Exclude)
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)

from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pyson import Eval, Bool, Not
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond import backend
from trytond.tools.multivalue import migrate_property
from trytond.tools import lstrip_wildcard
# from .exceptions import (
#     Invalidlocation, EraseError)
from datetime import datetime, timedelta
import random
from decimal import Decimal
import urllib

from trytond.config import config

if config.getboolean('attachment', 'filestore', default=True):
    file_id = 'image_id'
    store_prefix = config.get('attachment', 'store_prefix', default=None)
else:
    file_id = None
    store_prefix = None

class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    images = fields.One2Many('product.template.images', 'template', 'Galeria', size=4)
    variante = fields.Many2One('product.product.type', 'Variante', states={'readonly': Bool(Eval('products'))})
    description = fields.Text("Description")
    url = fields.Char('URL', help="La URL no deve tener espacios.")

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()
        cls.products.states['readonly'] = Not(Eval('variante', False))

    @fields.depends('name', 'url')
    def on_change_name(self, name=None):
        val = ''
        if self.name:
            val = self.name.lower().replace(' ', '-')
            val = val.replace('é', 'e').replace('á', 'a').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n').replace('.', '-')
            self.url = val

    def get_image(self):
        return self.products[0].get_image()

    @classmethod
    def default_products(cls):
        return None

    @classmethod
    def default_default_uom(cls):
        return 1

    @classmethod
    def search_random(cls, domain, limit=None):
        res_all = cls.search(domain)
        res = []
        if limit:
            if len(res_all) <= limit:
                return res_all
            for i in range(limit):
                res.append(res_all.pop(random.randint(0, len(res_all)-1)))
        else:
            return res_all
        return res


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    images = fields.One2Many('product.images', 'name', 'Galeria', size=4)
    url = fields.Char('URL', help="La URL no deve tener espacios ni mayusculas.")
    precio_lista = fields.Numeric(
            "Precio Lista", required=True, digits=(16,2),
            help="The standard price the product is sold at.")
    variante2 = fields.Many2One('product.product.type.option', 'Opcion', domain=[('type', '=', Eval('_parent_template.variante'))])

    def get_image(self):
        if self.images:
            return self.images[0].get_img()
        return False

    @classmethod
    def default_cost_price(cls):
        return Decimal(0)

    @classmethod
    def default_precio_lista(cls):
        return Decimal(0)


class ProductImages(sequence_ordered('sequence', 'Orden de Listado'),
                ModelView, ModelSQL):
    'Product Images'
    __name__ = 'product.images'

    name = fields.Many2One('product.product', 'Producto')
    image_name = fields.Function(fields.Char('File Name'), 'get_image_name')
    image_id = fields.Char('File ID', readonly=True, states={'invisible': True})
    image = fields.Binary('Imagen', filename='image_name',
        file_id=file_id, store_prefix=None)
    image_f = fields.Function(fields.Binary('Imagen', filename='image_name',
        file_id=file_id, store_prefix=None), 'get_image_f')

    @classmethod
    def convert_photo(cls, data):
        if data and Image:
            image = Image.open(BytesIO(data))
            # if image._getexif():
            #     exif = dict((ExifTags.TAGS[k], v) for k, v in image._getexif().items() if k in ExifTags.TAGS)
            #     if exif.get('Orientation'):
            #         if exif.get('Orientation')%2==0:
            #             image = image.rotate(90, expand=True)
            image.thumbnail((388, 500), Image.ANTIALIAS)
            data = BytesIO()
            if not (image.format):
                image.save(data, 'JPEG')
            else:
                image.save(data, image.format)
            data = fields.Binary.cast(data.getvalue())
        return data

    @classmethod
    def write(cls, *args):
        actions = iter(args)
        args = []
        for product, vals in zip(actions, actions):
            if 'image' in vals:
                vals['image'] = cls.convert_photo(vals['image'])
            args.extend((product, vals))

        super(ProductImages, cls).write(*args)

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if 'image' in values:
                values['image'] = cls.convert_photo(values['image'])

        return super(ProductImages, cls).create(vlist)

    def get_img(self):
        foto = None
        if self.image_id:
            return '/static/img2/' + self.image_id[:2] + '/' + self.image_id[2:4] + '/' + self.image_id

        if self.image:
            import base64
            foto = base64.b64encode(self.image).decode()
            return "data:image/JPEG;base64,"+foto
        return None

    def get_image_f(self, name):
        if self.image:
            return self.image
        return None

    def get_image_name(self, name):
        file_name = ''
        if self.name:
            if self.name.template.rec_name:
                file_name = self.name.template.rec_name + ".jpg"
            return file_name

    def get_rec_name(self, name):
        if self.name:
            return self.name


class TemplateImages(sequence_ordered('sequence', 'Orden de Listado'),
                     ModelView, ModelSQL):
    'Product Template Images'
    __name__ = 'product.template.images'

    template = fields.Many2One('product.template', 'Producto')
    image_name = fields.Function(fields.Char('File Name'), 'get_image_name')
    image_id = fields.Char('File ID', readonly=True, states={'invisible': True})
    image = fields.Binary('Imagen', filename='image_name',
                          file_id=file_id, store_prefix=None)
    image_f = fields.Function(fields.Binary('Imagen', filename='image_name',
        file_id=file_id, store_prefix=None), 'get_image_f')

    @classmethod
    def convert_photo(cls, data):
        if data and Image:
            image = Image.open(BytesIO(data))
            # if image._getexif():
            #     exif = dict((ExifTags.TAGS[k], v) for k, v in image._getexif().items() if k in ExifTags.TAGS)
            #     if exif.get('Orientation'):
            #         if exif.get('Orientation')%2==0:
            #             image = image.rotate(90, expand=True)
            image.thumbnail((388, 500), Image.ANTIALIAS)
            data = BytesIO()
            if not (image.format):
                image.save(data, 'JPEG')
            else:
                image.save(data, image.format)
            data = fields.Binary.cast(data.getvalue())
        return data

    @classmethod
    def write(cls, *args):
        actions = iter(args)
        args = []
        for product, vals in zip(actions, actions):
            if 'image' in vals:
                vals['image'] = cls.convert_photo(vals['image'])
            args.extend((product, vals))

        super(TemplateImages, cls).write(*args)

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:

            if 'image' in values:
                values['image'] = cls.convert_photo(values['image'])

        return super(TemplateImages, cls).create(vlist)

    def get_img(self):
        foto = None
        if self.image_id:
            return '/static/img2/' + self.image_id[:2] + '/' + self.image_id[2:4] + '/' + self.image_id

        if self.image:
            import base64
            foto = base64.b64encode(self.image).decode()
            return "data:image/JPEG;base64," + foto
        return None

    def get_image_f(self, name):
        if self.image:
            return self.image
        return None

    def get_image_name(self, name):
        file_name = ''
        if self.template:
            if self.template.rec_name:
                file_name = self.template.rec_name + ".jpg"
            return file_name

    def get_rec_name(self, name):
        if self.template:
            return self.template.name


class ProductType(ModelView, ModelSQL):
    'Product Type'
    __name__ = 'product.product.type'

    name = fields.Char('Nombre')
    opciones = fields.One2Many('product.product.type.option', 'type', 'Opcion')
    type_htmlElement = fields.Selection([
        ('select', 'Select'),
        ('radio', 'Radio')], 'Tipo elemento HTML')

    @classmethod
    def default_type_htmlElement(cls):
        return 'select'


class ProductTypeOption(ModelView, ModelSQL):
    'Product Type Option'
    __name__ = 'product.product.type.option'

    name = fields.Char('Nombre')
    type = fields.Many2One('product.product.type', 'Type')
    image_name = fields.Function(fields.Char('File Name'), 'get_image_name')
    image_id = fields.Char('File ID', readonly=True, states={'invisible': True})
    image = fields.Binary('Imagen', filename='image_name',
        file_id=file_id, store_prefix=None)
    image_f = fields.Function(fields.Binary('Imagen', filename='image_name',
        file_id=file_id, store_prefix=None), 'get_image_f')

    def get_img(self):
        foto = None
        if self.image_id:
            return '/static/img2/' + self.image_id[:2] + '/' + self.image_id[2:4] + '/' + self.image_id

        if self.image:
            import base64
            foto = base64.b64encode(self.image).decode()
            return "data:image/JPEG;base64,"+foto
        return None

    def get_image_name(self, name):
        file_name = ''
        if self.name:
            file_name = self.name + ".jpg"
        return file_name

    def get_image_f(self, name):
        if self.image:
            return self.image
        return None

    @classmethod
    def default_type_htmlElement(cls):
        return 'select'

