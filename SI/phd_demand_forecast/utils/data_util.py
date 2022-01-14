from datetime import date


def format_report_data(header, body, footer, **kwargs):
    return {
        "headerContent": header,
        "bodyContent": body,
        "tableContent": footer,
        **kwargs
    }


def format_header_data(id, model, name, descriptions, last_update, uom, **kwargs):
    return {
        "id": id,
        "model": model,
        "name": name,
        "uomText": uom,
        "descriptionList": descriptions,
        "lastUpdate": last_update,
        **kwargs
    }


def format_quantity_description_data(title, value, **kwargs):
    return {
        'text': title,
        'value': value,
        **kwargs
    }


def format_body_data(chart_config, **kwargs):
    return {
        "chartConfig": chart_config,
        **kwargs
    }


def format_table_data(title, model, headers, content, size=4, **kwargs):
    header_list = list(
        map(lambda x: x[0], sorted([(key, headers[key].get('sequence', 99)) for key in headers], key=lambda y: y[1])))
    return {
        "title": title,
        "size": size,
        "model": model,
        "headerData": headers,
        "headerListKey": header_list,
        "contentList": content,
        **kwargs
    }


def format_header_cell(key, title, is_number=False, is_clickable=False, sequence=1, **kwargs):
    return {
        key: {
            "name": title,
            "isNumber": is_number,
            "isClickable": is_clickable,
            "sequence": sequence,
            **kwargs
        }
    }


def format_content_cell(value, res_id=-1, **kwargs):
    return {
        "value": value,
        "id": res_id,
        **kwargs
    }


def format_float_number(number):
    return f'{number:,}'


def format_datetime(value):
    return value and value.strftime("%m/%d/%Y") or ''


def build_template_cell_sql(build_list=[]):
    return f"""'%s',json_build_object({",".join(list(map(lambda x: f"{x},%s", build_list)))} 'value', %s)"""


def build_template_select_sql(cells):
    return f"""array_agg(json_build_object({",".join(list(map(lambda x: x, cells)))}))"""
