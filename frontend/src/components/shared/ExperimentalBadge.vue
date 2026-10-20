<script setup lang="ts">
/**
 * 「试验中」气泡（v7.6 即梦协作 / 外部素材模式）。
 *
 * 即梦（Dreamina）协作自 v7.6 起提供，检查点提示词、批量导入与字幕对齐仍可能随版本
 * 调整，因此凡出现该功能的入口（创建面板的执行模式按钮 / 工具下拉、检查点协作卡片）
 * 都挂这枚气泡，文案与说明走 i18n（`experimentalBadge` / `experimentalBadgeHint`）。
 *
 * 用法：`<ExperimentalBadge />` 或 `<ExperimentalBadge size="sm" />`。
 */
import { t } from '@/i18n'

withDefaults(defineProps<{ size?: 'xs' | 'sm' }>(), { size: 'xs' })
</script>

<template>
  <span
    class="inline-flex shrink-0 items-center gap-0.5 rounded-full border border-amber-500/40 bg-amber-500/10 font-medium text-amber-400 align-middle whitespace-nowrap"
    :class="size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-1.5 py-0.5 text-[10px] leading-none'"
    :title="t('experimentalBadgeHint')"
  >🧪 {{ t('experimentalBadge') }}</span>
</template>
