from datetime import datetime

from pydantic import ConfigDict, Field, model_validator

from backend.common.enums import StatusType
from backend.common.schema import SchemaBase


class DictDataSchemaBase(SchemaBase):
    """字典数据基础模型"""

    type_id: int = Field(description='字典类型 ID')
    label: str | None = Field(None, max_length=2000, description='兼容字典标签')
    value: str = Field(min_length=1, max_length=128, description='稳定字典 Key')
    label_zh_cn: str | None = Field(None, max_length=2000, description='简体中文值')
    label_en_us: str | None = Field(None, max_length=2000, description='英文值')
    color: str | None = Field(None, description='标签颜色')
    sort: int = Field(description='排序')
    status: StatusType = Field(description='状态')
    remark: str | None = Field(None, description='备注')

    @model_validator(mode='after')
    def normalize_localized_labels(self):
        self.label_zh_cn = (self.label_zh_cn or self.label or '').strip() or None
        self.label_en_us = (self.label_en_us or '').strip() or None
        if not self.label_zh_cn:
            raise ValueError('label_zh_cn or legacy label is required')
        self.label = self.label_zh_cn
        return self


class CreateDictDataParam(DictDataSchemaBase):
    """创建字典数据参数"""


class UpdateDictDataParam(DictDataSchemaBase):
    """更新字典数据参数"""


class DeleteDictDataParam(SchemaBase):
    """删除字典数据参数"""

    pks: list[int] = Field(description='字典数据 ID 列表')


class GetDictDataDetail(DictDataSchemaBase):
    """字典数据详情"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='字典数据 ID')
    type_code: str = Field(description='字典类型编码')
    created_time: datetime = Field(description='创建时间')
    updated_time: datetime | None = Field(None, description='更新时间')
