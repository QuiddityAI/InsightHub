<script setup>
import Chip from 'primevue/chip';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { available_filter_operators } from '../../utils/utils'
const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
  },
  methods: {
    remove_filter(index) {
      this.appStateStore.settings.search.filters.splice(index, 1)
      this.eventBus.emit("search_filters_changed")
    },
    get_filter_label(filter) {
      let field_name = ""
      if (filter.field === '_descriptive_text_fields') {
        field_name = 'Descriptive Text'
      } else {
        const field_details = this.appStateStore.datasets[filter.dataset_id].schema.object_fields[filter.field]
        field_name = field_details.name || field_details.identifier
      }
      const operator = available_filter_operators.find(op => op.id === filter.operator)
      return `${field_name} ${operator.title} '${filter.value}'`
    },
  },
}
</script>

<template>
  <div v-if="appState.settings.search.filters.length" class="mt-3 flex flex-row flex-wrap gap-2">
    <Chip v-for="filter, index in appState.settings.search.filters"
      :label="get_filter_label(filter)"
      removable @remove="remove_filter(index)">
    </Chip>
  </div>

</template>

<style scoped>
</style>
