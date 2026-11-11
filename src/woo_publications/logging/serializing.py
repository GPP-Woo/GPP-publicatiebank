from itertools import chain

from django.db import models


def model_to_dict(instance, ignore_fields: tuple = ()):
    """
    Modified version of django.forms.model_to_dict.

    * it doesn't skip non-editable fields
    * it serializes related objects to their PK instead of passing model instances
    """
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        if f.name in ignore_fields:
            continue

        value = f.value_from_object(instance)
        match f:
            case models.ManyToManyField():
                value = [obj.pk for obj in value]
            case models.FileField():
                value = value.name
            case _:
                pass
        data[f.name] = value

    return data


def serialize_instance(instance: models.Model, ignore_fields: tuple = ()):
    return model_to_dict(instance, ignore_fields=ignore_fields)
