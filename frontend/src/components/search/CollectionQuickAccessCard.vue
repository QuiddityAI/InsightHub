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
  <div class="flex flex-col bg-white shadow-sm rounded-md px-5 py-3">
    <div class="flex flex-row items-center justify-between">
      <h3 class="text-sm text-gray-500">Quick Access: My Favorites</h3>
    </div>

    <div class="flex flex-row items-center justify-between">
      Extract - Recommend - Export - Chat
    </div>
  </div>

</template>

<style scoped>
</style>
