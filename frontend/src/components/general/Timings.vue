<script setup>
import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
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
  },
}
</script>

<template>
  <div v-if="appState.show_timings" class="absolute bottom-0 right-0 text-right">
    <ul role="list">
      <li v-for="item in appState.search_timings" :key="item.part" class="text-gray-300">
        {{ item.part }}: {{ item.duration.toFixed(2) }} s
      </li>
    </ul>
    <hr />
    <ul role="list">
      <li v-for="item in appState.map_timings" :key="item.part" class="text-gray-300">
        {{ item.part }}: {{ item.duration.toFixed(2) }} s
      </li>
    </ul>
  </div>

</template>

<style scoped>
</style>
