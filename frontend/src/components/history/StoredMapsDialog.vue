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
  inject: ["eventBus", "dialogRef"],
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
      Log in to store maps
    </Message>

    <div v-if="appState.map_id && appState.logged_in" class="my-2 flex items-stretch">
      <button
        class="flex-auto rounded-md border-0 px-2 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="appState.store_current_map">
        Add Current Map
      </button>
    </div>

    <ul v-if="appState.stored_maps.length !== 0" role="list" class="pt-3">
      <li
        v-for="stored_map in appState.stored_maps"
        :key="stored_map.name"
        class="justify-between pb-3">
        <div class="flex flex-row gap-3">
          <span class="font-medium text-gray-500">{{ stored_map.name }}</span>
          <div class="flex-1"></div>
          <button
            @click="appState.delete_stored_map(stored_map.id)"
            class="text-sm font-light text-gray-500 hover:text-blue-500/50">
            Delete
          </button>
          <button
            @click="appState.show_stored_map(stored_map.id); dialogRef.close()"
            class="text-sm font-light text-gray-500 hover:text-blue-500/50">
            Show Map
          </button>
        </div>
      </li>
    </ul>
    <div
      v-if="appState.stored_maps.length === 0"
      class="flex h-20 flex-col place-content-center text-center">
      <p class="flex-none text-gray-400">No Stored Maps Yet</p>
    </div>
  </div>
</template>

<style scoped>
</style>
