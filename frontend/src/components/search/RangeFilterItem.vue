<script setup>
import Slider from 'primevue/slider';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { httpClient } from "../../api/httpClient"
import { debounce } from "../../utils/utils"

const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["range_filter"],
  emits: [],
  data() {
    return {
      min_value: 0,
      max_value: 10,
      value: [0, 10],
      step_size: 1,
      use_integers: false,
      update_filter_debounced: debounce(() => {
        this.update_filter()
      }, 500),
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.update_boundaries()
  },
  watch: {
    min_value(new_val, old_val) {
      this.update_filter_debounced()
    },
    max_value(new_val, old_val) {
      this.update_filter_debounced()
    },
    value(new_val, old_val) {
      this.update_filter_debounced()
    },
  },
  methods: {
    update_boundaries() {
      let max_value = -Infinity
      let min_value = Infinity
      const item_details = this.appStateStore.map_item_details
      for (const ds_and_item_id of this.appStateStore.search_result_ids) {
        const ds_items = item_details[ds_and_item_id[0]]
        if (!ds_items) continue
        const item = ds_items[ds_and_item_id[1]]
        const value = item[this.range_filter.field]
        if (value > max_value) {
          max_value = value
        }
        if (value < min_value) {
          min_value = value
        }
      }
      this.max_value = max_value
      this.min_value = min_value
      this.value = [min_value, max_value]
      this.use_integers = (max_value - min_value) > 5
      this.step_size = this.use_integers ? 1 : (max_value - min_value) / 100
    },
    remove_filter(index) {
      this.mapStateStore.visibility_filters.splice(index, 1)
      this.eventBus.emit("visibility_filters_changed")
    },
    update_filter() {
      this.mapStateStore.visibility_filters = this.mapStateStore.visibility_filters.filter(
        (filter_item) => !(filter_item.is_range_filter && filter_item.field === this.range_filter.field)
      )
      if (this.value[0] === this.min_value && this.value[1] === this.max_value) {
        this.eventBus.emit("visibility_filters_changed")
        return
      }
      this.mapStateStore.visibility_filters.push({
        display_name: `${this.range_filter.display_name}: ${this.value[0]} - ${this.value[1]}`,
        is_range_filter: true,
        field: this.range_filter.field,
        hide_remove_button: true,
        filter_fn: (item) => item[this.range_filter.field] >= this.value[0] && item[this.range_filter.field] <= this.value[1],
      })
      this.eventBus.emit("visibility_filters_changed")
    },
  },
}
</script>

<template>
  <div class="mx-2 flex flex-row gap-2 items-center">
    <span class="flex-none text-sm text-gray-500">{{ range_filter.display_name }}:</span>
    <span class="flex-none text-sm text-gray-500">{{ value[0].toFixed(use_integers ? 0 : 2) }}</span>
    <div class="flex-1 px-4">
      <Slider v-model="value" :min="min_value" :max="max_value" :step="step_size" range class="" />
    </div>
    <span class="flex-none text-sm text-gray-500">{{ value[1].toFixed(use_integers ? 0 : 2) }}</span>
  </div>

</template>

<style scoped>
</style>
