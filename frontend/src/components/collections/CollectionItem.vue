<script setup>
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"

const appState = useAppStateStore()
</script>

<script>
import { httpClient } from "../../api/httpClient"

export default {
  props: ["dataset_id", "item_id", "is_positive", "show_remove_button"],
  emits: ["remove"],
  data() {
    return {
      item: {},
      rendering: null,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  watch: {
    dataset_id() {
      this.init()
    },
    item_id() {
      this.init()
    },
  },
  mounted() {
    this.init()
  },
  methods: {
    init() {
      const that = this
      if (!this.dataset_id || !this.item_id) return
      if (this.item._dataset_id === this.dataset_id && this.item._id === this.item_id) return
      this.rendering = this.appStateStore.datasets[this.dataset_id]?.schema.result_list_rendering
      if (!this.rendering) {
        this.item = {}
        return
      }
      const payload = {
        dataset_id: this.dataset_id,
        item_id: this.item_id,
        fields: this.rendering.required_fields,
      }
      httpClient.post("/data_backend/document/details_by_id", payload).then(function (response) {
        that.item = response.data
      })
    },
  },
}
</script>

<template>
  <div v-if="rendering" class="rounded bg-gray-100/50 p-3 flex flex-row gap-2 cursor-pointer"
    @click="appState.show_document_details([dataset_id, item_id])">
    <div class="flex-1">
      <img v-if="rendering.icon(item)" :src="rendering.icon(item)" class="h-5 w-5 mr-2 inline" />
      <p class="text-sm font-medium leading-normal text-gray-90 inline" v-html="rendering.title(item)"></p>
      <p class="mt-1 text-xs leading-relaxed text-gray-500" v-html="rendering.subtitle(item)"></p>

      <div class="flex-1"></div>
      <div class="mt-2 flex flex-row items-center">
        <span class="mr-3 rounded-xl bg-gray-200 px-2 text-xs text-gray-500">
          {{ appState.datasets[dataset_id]?.name }}
        </span>
        <button v-if="show_remove_button" @click.stop="$emit('remove')" class="text-sm text-gray-500">Remove</button>
      </div>
    </div>
    <div v-if="rendering.image(item)" class="flex-none w-24 flex flex-col justify-center">
      <img class="w-full rounded-lg shadow-md" :src="rendering.image(item)" />
    </div>
  </div>
</template>
