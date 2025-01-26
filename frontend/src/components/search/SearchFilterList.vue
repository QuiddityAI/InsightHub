<script setup>
import Chip from 'primevue/chip';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { available_filter_operators, additional_filter_operators } from '../../utils/utils'
const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["filters", "removable"],
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
      this.filters.splice(index, 1)
      this.eventBus.emit("search_filters_changed")
    },
    get_filter_label(filter) {
      if (filter.label) {
        return filter.label
      }
      let field_name = ""
      if (filter.field === '_descriptive_text_fields') {
        field_name = this.$t('general.descriptive-text-fields')
      } else if (filter.field === '_parent') {
        field_name = 'Parent'
      } else if (filter.field === '_all_parents') {
        field_name = 'Any Parent'
      } else {
        const field_details = this.appStateStore.datasets[filter.dataset_id].schema.object_fields[filter.field]
        field_name = field_details.name || field_details.identifier
      }
      const operators = available_filter_operators.concat(additional_filter_operators)
      const operator = operators.find(op => op.id === filter.operator)
      return `${field_name} ${operator.title} '${filter.value}'`
    },
  },
}
</script>

<template>
  <div v-if="filters  && filters.length" class="flex flex-row flex-wrap gap-2">
    <Chip v-for="filter, index in filters"
      :removable="removable" @remove="remove_filter(index)">
      <span class="text-xs">{{ get_filter_label(filter) }}</span>
    </Chip>
  </div>

</template>

<style scoped>
</style>
