<script setup>
import { useToast } from 'primevue/usetoast';
import Button from 'primevue/button';
import Message from 'primevue/message';
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
  <div>
    <Message v-if="!appState.logged_in" severity="warn">
      Log in to see the history
    </Message>
    <ul v-if="Object.keys(appState.search_history).length !== 0" role="list" class="pt-3">
      <li
        v-for="history_item in appState.search_history.slice().reverse()"
        :key="history_item.id"
        class="justify-between pb-3">
        <div class="flex flex-row gap-3">
          <span class="font-medium text-gray-500" v-html="history_item.display_name"></span>
          <div class="flex-1"></div>
          <button
            @click="appState.run_search_from_history(history_item)"
            class="text-sm font-light text-gray-500 hover:text-blue-500/50">
            Run again
          </button>
        </div>
      </li>
    </ul>
    <div
      v-if="Object.keys(appState.search_history).length === 0"
      class="flex h-20 flex-col place-content-center text-center">
      <p class="flex-none text-gray-400">No History Yet</p>
    </div>
  </div>
</template>

<style scoped>
</style>
