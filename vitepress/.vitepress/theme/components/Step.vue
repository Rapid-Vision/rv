<script setup lang="ts">
defineProps<{
  title?: string
  optional?: boolean
}>()
</script>

<template>
  <li class="vp-step">
    <div class="vp-step__marker" aria-hidden="true"></div>

    <div class="vp-step__content">
      <div v-if="title" class="vp-step__title">
        <span class="vp-step__titleText">{{ title }}</span>
        <span v-if="optional" class="vp-step__optional">Optional</span>
      </div>

      <div class="vp-step__body">
        <slot />
      </div>
    </div>
  </li>
</template>
