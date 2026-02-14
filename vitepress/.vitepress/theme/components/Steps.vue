<script setup lang="ts">
/**
 * Usage:
 * <Steps>
 *   <Step title="Install">...</Step>
 *   <Step title="Configure">...</Step>
 * </Steps>
 */
withDefaults(
  defineProps<{
    dense?: boolean
  }>(),
  { dense: false }
)
</script>

<template>
  <div class="vp-steps" :class="{ dense }">
    <ol class="vp-steps__list">
      <slot />
    </ol>
  </div>
</template>
