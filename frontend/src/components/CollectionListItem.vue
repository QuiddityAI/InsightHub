
<script>
import httpClient from '../api/httpClient';

export default {
  props: ["item_id", "schema_id", "isPositive"],
  emits: ["remove"],
  data() {
    return {
      item_details: {},
      required_fields: ["title", "container_title", "issued_year"],  // FIXME: hardcoded
    }
  },
  mounted() {
    const that = this
    const payload = {
      schema_id: this.schema_id,
      item_id: this.item_id,
      fields: this.required_fields
    }
    httpClient.post("/data_backend/document/details_by_id", payload)
      .then(function (response) {
        that.item_details = response.data
      })
  },
}
</script>


<template>
<div class="rounded px-3 py-2" :class="{'bg-green-100/50': isPositive, 'bg-red-100/50': !isPositive}">
  <p class="text-sm font-medium leading-6 text-gray-900"><div v-html="item_details.title"></div></p>
  <p class="truncate text-xs leading-5 text-gray-500">{{ item_details.container_title }}, {{ item_details.issued_year }}</p>
  <button @click="$emit('remove')" class="text-sm text-gray-500">Remove</button>
</div>
</template>