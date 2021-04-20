# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from . import product
# from . import category

def register():
    Pool.register(
        product.ProductImages,
        product.TemplateImages,
        product.Product,
        product.Template,
        product.ProductType,
        product.ProductTypeOption,
        # category.Category,
        module='product_image_galery_option', type_='model')
