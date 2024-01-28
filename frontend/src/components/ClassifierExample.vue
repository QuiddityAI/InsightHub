<script setup>
import { mapStores } from "pinia"
import { useAppStateStore } from "../stores/settings_store"

const appState = useAppStateStore()
</script>

<script>
import httpClient from "../api/httpClient"

export default {
  props: ["item_id", "is_positive"],
  emits: ["remove"],
  data() {
    return {
      item: {},
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {
    const that = this
    const payload = {
      dataset_id: this.appStateStore.settings.dataset_id,
      item_id: this.item_id,
      fields: this.appStateStore.classifier_example_rendering.required_fields,
    }
    httpClient.post("/data_backend/document/details_by_id", payload).then(function (response) {
      that.item = response.data
    })
  },
}
</script>

<template>
  <div
    class="rounded px-3 py-2"
    :class="{ 'bg-green-100/50': is_positive, 'bg-red-100/50': !is_positive }">
    <p
      class="text-sm font-medium leading-6 text-gray-900"
      v-html="appState.classifier_example_rendering.title(item)"></p>
    <p
      class="truncate text-xs leading-5 text-gray-500"
      v-html="appState.classifier_example_rendering.subtitle(item)"></p>
    <img
      v-if="appState.classifier_example_rendering.image(item)"
      class="h-24"
      :src="appState.classifier_example_rendering.image(item)" />
    <button @click="$emit('remove')" class="text-sm text-gray-500">Remove</button>
  </div>
</template>
