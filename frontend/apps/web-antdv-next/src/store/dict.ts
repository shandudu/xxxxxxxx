import type { DictDataResult } from '#/plugins/dict/api';
import type { DictOptionsParams } from '#/utils/dict';

import { reactive, watch } from 'vue';

import { $t, i18n } from '@vben/locales';

import { defineStore } from 'pinia';

import { generateDictCacheKey } from '#/utils/dict';

export interface DictOption {
  disabled?: boolean;
  label: string;
  value: boolean | number | string;
  color?: string;
}

export function localizedDictLabel(
  item: DictDataResult,
  locale = String(i18n.global.locale.value),
): string {
  const candidate = locale === 'en-US'
    ? (item.label_en_us || item.label_zh_cn || item.label || item.value)
    : (item.label_zh_cn || item.label || item.label_en_us || item.value);
  return $t(candidate);
}

function interpolate(text: string, params: Record<string, unknown> = {}) {
  return text.replace(/\{([^{}]+)\}/g, (matched, key: string) =>
    Object.prototype.hasOwnProperty.call(params, key) ? String(params[key]) : matched,
  );
}

export function dictToOptions(
  data: DictDataResult[],
  params: DictOptionsParams,
): DictOption[] {
  const { asBoolean = false, asNumber = false, asString = false } = params;

  return data.map((item) => {
    let value: boolean | number | string = item.value;
    if (asBoolean) {
      value = item.value === 'true';
    } else if (asNumber) {
      value = Number(item.value);
    } else if (asString) {
      // asString 时保持原样，因为 value 本身就是 string 类型
      value = item.value;
    }

    return {
      disabled: item.status === 0,
      label: localizedDictLabel(item),
      value,
      color: item.color,
    };
  });
}

export const useDictStore = defineStore('dict', () => {
  const dictOptionsMap = reactive(new Map<string, DictOption[]>());
  const rawDictMap = reactive(new Map<string, DictDataResult[]>());
  const dictParamsMap = reactive(new Map<string, DictOptionsParams>());
  const dictNameMap = reactive(new Map<string, string>());
  const dictRequestCache = reactive(
    new Map<string, Promise<DictDataResult[]>>(),
  );

  function getDictOptions(
    dictName: string,
    params: DictOptionsParams,
  ): DictOption[] {
    if (!dictName) return [];

    const cacheKey = generateDictCacheKey(dictName, params);

    if (!dictOptionsMap.has(cacheKey)) {
      dictOptionsMap.set(cacheKey, []);
    }

    return dictOptionsMap.get(cacheKey) || [];
  }

  function setDictInfo(
    dictName: string,
    dictValue: DictDataResult[],
    params: DictOptionsParams,
  ) {
    const cacheKey = generateDictCacheKey(dictName, params);
    rawDictMap.set(dictName, dictValue);
    dictParamsMap.set(cacheKey, params);
    dictNameMap.set(cacheKey, dictName);
    const nextOptions = dictToOptions(dictValue, params);

    if (dictOptionsMap.has(cacheKey)) {
      dictOptionsMap.get(cacheKey)?.splice(0, Number.POSITIVE_INFINITY, ...nextOptions);
    } else {
      dictOptionsMap.set(cacheKey, nextOptions);
    }
  }

  function getLocalizedText(
    dictName: string,
    value: string,
    fallback = value,
    params: Record<string, unknown> = {},
  ): string {
    const item = rawDictMap.get(dictName)?.find((entry) => entry.value === value);
    return interpolate(item ? localizedDictLabel(item) : fallback, params);
  }

  watch(
    () => i18n.global.locale.value,
    () => {
      for (const [cacheKey, params] of dictParamsMap) {
        const dictName = dictNameMap.get(cacheKey);
        if (!dictName) continue;
        const raw = rawDictMap.get(dictName);
        const current = dictOptionsMap.get(cacheKey);
        if (raw && current) current.splice(0, current.length, ...dictToOptions(raw, params));
      }
    },
  );

  function resetCache() {
    dictOptionsMap.clear();
    dictRequestCache.clear();
    rawDictMap.clear();
    dictParamsMap.clear();
    dictNameMap.clear();
  }

  function $reset() {
    // doNothing
  }

  return {
    $reset,
    dictOptionsMap,
    dictRequestCache,
    getLocalizedText,
    getDictOptions,
    setDictInfo,
    resetCache,
    rawDictMap,
  };
});
