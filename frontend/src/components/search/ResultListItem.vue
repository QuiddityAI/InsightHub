<script setup>
import { httpClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["initial_item", "rendering"],
  data() {
    return {
      item: this.initial_item,
      loading_item: false,
    }
  },
  watch: {
    initial_item() {
      this.item = this.initial_item
      this.getFullItem()
    },
  },
  methods: {
    getFullItem() {
      if (!this.item || !this.item._id) return
      const that = this

      const payload = {
        dataset_id: this.item._dataset_id,
        item_id: this.item._id,
        fields: this.appStateStore.datasets[this.item._dataset_id].result_list_rendering.required_fields,
      }
      this.loading_item = true
      httpClient
        .post("/data_backend/document/details_by_id", payload)
        .then(function (response) {
          that.item = {
            ...that.item,
            ...response.data,
          }
        })
        .finally(function () {
          that.loading_item = false
        })
    },
  },
  mounted() {
    this.getFullItem()
  },
  computed: {
    ...mapStores(useAppStateStore),
  }
}
</script>

<template>
  <div class="rounded bg-gray-100/50 p-3">
    <p class="text-sm font-medium leading-6 text-gray-900" v-html="rendering.title(item)"></p>
    <p class="mt-1 text-xs leading-5 text-gray-500" v-html="rendering.subtitle(item)"></p>
    <p class="mt-2 text-xs leading-5 text-gray-700" v-html="rendering.body(item)"></p>
    <p class="mt-2 text-xs leading-5 text-gray-700" v-if="rendering.url(item)">
      <a :href="rendering.url(item)">Link</a>
    </p>
    <img v-if="rendering.image(item)" class="h-24" :src="rendering.image(item)" />
    <span class="mr-3 rounded-xl bg-gray-200 px-2 text-xs text-gray-500">
      {{ item._reciprocal_rank_score.toFixed(2) }}
    </span>
    <span
      v-for="origin in item._origins"
      class="mr-3 rounded-xl bg-gray-200 px-2 text-xs text-gray-500">
      {{ origin.score.toFixed(2) }}, {{ origin.type }}: {{ origin.field }}, q =
      {{ origin.query }}
    </span>
    <span v-if="appState.settings.search.dataset_ids.length > 1" class="mr-3 rounded-xl bg-gray-200 px-2 text-xs text-gray-500">
      {{ appState.datasets[item._dataset_id].name }}
    </span>
  </div>
</template>
