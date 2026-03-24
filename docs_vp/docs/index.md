---
layout: page
title: Redirecting...
head:
  - - meta
    - http-equiv: refresh
      content: 0; url=/en/
---

<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  window.location.replace('/en/')
})
</script>

Redirecting to the English docs...
