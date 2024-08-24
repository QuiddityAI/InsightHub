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
    is_stored() {
      return this.appStateStore.stored_maps.filter(map => map.id === this.appStateStore.map_id).length > 0
    },
    share_url() {
      return window.location
    }
  },
  mounted() {
  },
  watch: {
  },
  methods: {
    copy_share_url() {
      if (!window.navigator.clipboard) {
        window.prompt('Copy to clipboard: Ctrl+C, Enter', this.share_url)
      } else {
        navigator.clipboard.writeText(this.share_url)
        toast.add({severity: 'success', summary: 'Success', detail: 'Link copied to clipboard', life: 3000})
      }
    },
  },
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <Message v-if="!appState.logged_in" severity="warn">
      Log in to store maps
    </Message>

    <div v-if="appState.map_id && appState.logged_in" class="flex flex-row items-center">
      <Button
        :outlined="!is_stored"
        @click="is_stored ? appState.delete_stored_map(appState.map_id) : appState.store_current_map()">
        {{ is_stored ? 'Stored ✓' : 'Store this map' }}
      </Button>
    </div>

    <div class="flex flex-row gap-3 items-center">
      <span>Share Link:</span>
      <input
        class="flex-auto rounded-md border-0 px-2 py-1.5 text-gray-600 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="text"
        :disabled="!is_stored"
        :value="is_stored ? share_url : 'You need to store the map first'"
        readonly>
      <Button
        class="rounded-md border-0 px-2 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        :disabled="!is_stored"
        @click="copy_share_url()">
        Copy
      </Button>
    </div>

    <span>
      You can share this link with colleagues and friends or on social media to show the map you created.
    </span>

  </div>
</template>

<style scoped>
</style>
