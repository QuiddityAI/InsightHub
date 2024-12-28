<script setup>
import Slider from 'primevue/slider';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from '../../stores/collection_store';
import { httpClient } from "../../api/httpClient"
import { FieldType, debounce } from "../../utils/utils"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["range_filter", "dataset_ids"],
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
    ...mapStores(useCollectionStore),
  },
  mounted() {
    this.update_boundaries()
    this.eventBus.on("collection_items_loaded", this.update_boundaries)
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
      this.collectionStore.get_value_range(this.range_filter.field, (value_range) => {
        this.min_value = value_range.min
        this.max_value = value_range.max
        this.value = [value_range.min, value_range.max]
        for (const filter of this.collectionStore.collection.filters) {
          if (filter.field === this.range_filter.field) {
            if (filter.filter_type === "metadata_value_gte") {
              this.value[0] = filter.value
            } else if (filter.filter_type === "metadata_value_lte") {
              this.value[1] = filter.value
            }
          }
        }
        const any_ds_field_is_integer = this.dataset_ids.some(
          (ds_id) => this.appStateStore.datasets[ds_id]?.schema.object_fields[this.range_filter.field]?.field_type === FieldType.INTEGER
        )
        this.use_integers = any_ds_field_is_integer || (max_value - min_value) > 5
        this.step_size = this.use_integers ? 1 : (max_value - min_value) / 100
      })

      // if (this.appStateStore.search_result_ids.length === 0) {
      //   this.max_value = 10
      //   this.min_value = 0
      //   this.value = [0, 10]
      //   this.use_integers = true
      //   this.step_size = 1
      //   return
      // }
    },
    remove_filter(index) {
      this.mapStateStore.visibility_filters.splice(index, 1)
      this.eventBus.emit("visibility_filters_changed")
    },
    update_filter() {
      const min_filter_uid = `metadata_value_gte__${this.range_filter.field}`
      if (this.value[0] === this.min_value) {
        this.collectionStore.remove_filter(min_filter_uid)
      } else {
        const range_filter = {
          uid: min_filter_uid,
          display_name: `${this.range_filter.display_name} >= ${this.value[0]}`,
          removable: false,
          filter_type: "metadata_value_gte",
          value: this.value[0],
          field: this.range_filter.field,
        }
        this.collectionStore.add_filter(range_filter)
      }
      const max_filter_uid = `metadata_value_lte__${this.range_filter.field}`
      if (this.value[1] === this.max_value) {
        this.collectionStore.remove_filter(max_filter_uid)
      } else {
        const range_filter = {
          uid: max_filter_uid,
          display_name: `${this.range_filter.display_name} <= ${this.value[1]}`,
          removable: false,
          filter_type: "metadata_value_lte",
          value: this.value[1],
          field: this.range_filter.field,
        }
        this.collectionStore.add_filter(range_filter)
      }
    },
  },
}
</script>

<template>
  <div class="mx-2 flex flex-row gap-2 items-center">
    <span class="flex-none text-xs text-gray-400">{{ range_filter.display_name }}:</span>
    <span class="flex-none text-xs text-gray-500">{{ value[0].toFixed(use_integers ? 0 : 2) }}</span>
    <div class="flex-1 px-4 opacity-50">
      <Slider v-model="value" :min="min_value" :max="max_value" :step="step_size" range class="" />
    </div>
    <span class="flex-none text-xs text-gray-500">{{ value[1].toFixed(use_integers ? 0 : 2) }}</span>
  </div>

</template>

<style scoped>
</style>
