from backend.plugin.dict.model import DictData
from backend.plugin.dict.schema.dict_data import CreateDictDataParam


def test_bilingual_dictionary_columns_registered() -> None:
    assert DictData.__table__.c.label_zh_cn.type.__class__.__name__ == 'Text'
    assert DictData.__table__.c.label_en_us.type.__class__.__name__ == 'Text'
    assert DictData.__table__.c.value.type.length == 128


def test_chinese_value_populates_legacy_label() -> None:
    data = CreateDictDataParam(
        type_id=1,
        value='release_confirm',
        label_zh_cn='确定发布工单 {workOrderNo} 吗？',
        label_en_us='Release work order {workOrderNo}?',
        color=None,
        sort=0,
        status=1,
        remark=None,
    )
    assert data.label == data.label_zh_cn
    assert data.value == 'release_confirm'


def test_legacy_label_remains_compatible() -> None:
    data = CreateDictDataParam(
        type_id=1,
        label='common.enabled',
        value='1',
        color='success',
        sort=0,
        status=1,
        remark=None,
    )
    assert data.label_zh_cn == 'common.enabled'
    assert data.label_en_us is None
